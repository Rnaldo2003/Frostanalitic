"""
reports_api.py — FrostAnalitic
Exportación de reportes para la tesis: CSV crudo de sesiones y un PDF
resumen con las estadísticas y las gráficas del módulo de ciencia de
datos (si ya se generaron con ds/ml_model.py).

Requiere sesión iniciada (rol tecnico o admin) porque expone datos de
diagnósticos reales, no solo estadísticas agregadas.
"""
import csv
import io
import os
from datetime import datetime

from flask import Blueprint, Response, jsonify
from auth import roles_required
from models.models import db, Sesion, Falla, Equipo

reports_bp = Blueprint('reports_api', __name__, url_prefix='/api/export')

BASE = os.path.dirname(os.path.abspath(__file__))
GRAFICAS_DIR = os.path.join(BASE, 'ds', 'output')


@reports_bp.route('/csv')
@roles_required('admin', 'tecnico')
def exportar_csv():
    equipos = {e.id: e.nombre for e in Equipo.query.all()}
    fallas = {f.id: f.nombre for f in Falla.query.all()}

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'id', 'fecha', 'equipo', 'falla_diagnosticada', 'probabilidad',
        'fue_correcto', 'falla_real', 'nivel_usuario', 'nota_usuario',
    ])
    for s in Sesion.query.order_by(Sesion.id).all():
        writer.writerow([
            s.id,
            s.created_at.strftime('%Y-%m-%d %H:%M:%S') if s.created_at else '',
            equipos.get(s.equipo_id, ''),
            fallas.get(s.falla_id, ''),
            s.probabilidad if s.probabilidad is not None else '',
            {True: 'si', False: 'no', None: 'sin_evaluar'}[s.fue_correcto],
            fallas.get(s.falla_real_id, '') if s.falla_real_id else '',
            s.nivel_usuario or '',
            (s.nota_usuario or '').replace('\n', ' '),
        ])

    nombre_archivo = f'frostanalitic_sesiones_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    return Response(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{nombre_archivo}"'},
    )


@reports_bp.route('/pdf')
@roles_required('admin', 'tecnico')
def exportar_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
        )
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        return jsonify({'error': 'reportlab no está instalado en el servidor.'}), 500

    total = Sesion.query.count()
    correctas = Sesion.query.filter_by(fue_correcto=True).count()
    incorrectas = Sesion.query.filter_by(fue_correcto=False).count()
    precision = round(correctas / total * 100, 1) if total else 0
    top_fallas = (Falla.query
                  .order_by(Falla.veces_diagnosticada.desc())
                  .limit(10).all())

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             topMargin=2 * cm, bottomMargin=2 * cm,
                             leftMargin=2 * cm, rightMargin=2 * cm)
    estilos = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph('FrostAnalitic — Reporte de Diagnóstico', estilos['Title']))
    elementos.append(Paragraph(
        f'Generado el {datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC', estilos['Normal']))
    elementos.append(Spacer(1, 0.6 * cm))

    resumen = [
        ['Total de diagnósticos', str(total)],
        ['Confirmados correctos', str(correctas)],
        ['Corregidos por el usuario', str(incorrectas)],
        ['Precisión global observada', f'{precision}%'],
    ]
    tabla_resumen = Table(resumen, colWidths=[9 * cm, 6 * cm])
    tabla_resumen.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#333333')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef2f7')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 0.8 * cm))

    elementos.append(Paragraph('Fallas más diagnosticadas', estilos['Heading2']))
    filas_fallas = [['Falla', 'Veces', 'Precisión BD']]
    for f in top_fallas:
        prec_f = (round(f.veces_correcta / f.veces_diagnosticada * 100, 1)
                  if f.veces_diagnosticada else '—')
        filas_fallas.append([f.nombre, str(f.veces_diagnosticada or 0),
                              f'{prec_f}%' if prec_f != '—' else '—'])
    tabla_fallas = Table(filas_fallas, colWidths=[9 * cm, 3 * cm, 3 * cm])
    tabla_fallas.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#333333')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5be3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_fallas)

    graficas = [
        ('comparacion_modelos.png', 'Comparación de modelos de ML'),
        ('evolucion_precision.png', 'Evolución de precisión con el uso'),
        ('fallas_frecuentes.png', 'Fallas más frecuentes'),
        ('matriz_confusion.png', 'Matriz de confusión'),
    ]
    graficas_incluidas = 0
    for archivo, titulo in graficas:
        ruta = os.path.join(GRAFICAS_DIR, archivo)
        if os.path.exists(ruta):
            elementos.append(Spacer(1, 0.6 * cm))
            elementos.append(Paragraph(titulo, estilos['Heading2']))
            elementos.append(Image(ruta, width=16 * cm, height=8 * cm))
            graficas_incluidas += 1
    if not graficas_incluidas:
        elementos.append(Spacer(1, 0.6 * cm))
        elementos.append(Paragraph(
            'Las gráficas del módulo de ciencia de datos aún no se han generado '
            '(ejecuta ds/ml_model.py en el servidor para incluirlas).',
            estilos['Italic']))

    doc.build(elementos)
    buffer.seek(0)
    nombre_archivo = f'frostanalitic_reporte_{datetime.utcnow().strftime("%Y%m%d")}.pdf'
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{nombre_archivo}"'},
    )
