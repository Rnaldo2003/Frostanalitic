-- ============================================================
--  FrostAnalitic — Schema v2  (MySQL 8+)
--  Incluye: equipos, síntomas, árbol de decisiones dinámico,
--           fallas, soluciones, sesiones de diagnóstico y
--           sistema de aprendizaje por retroalimentación.
-- ============================================================

CREATE DATABASE IF NOT EXISTS `frostanalitic`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `frostanalitic`;

-- ── Equipos ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `equipos` (
  `id`     INT          NOT NULL AUTO_INCREMENT,
  `nombre` VARCHAR(100) NOT NULL,
  `icono`  VARCHAR(10)  DEFAULT '🔧',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `equipos` (`nombre`, `icono`) VALUES
  ('Refrigerador',      '🧊'),
  ('Congelador',        '🥶'),
  ('Aire Acondicionado','💨'),
  ('Enfriador Comercial','🏪'),
  ('Cuarto Frío',       '🏭')
ON DUPLICATE KEY UPDATE `nombre`=VALUES(`nombre`);

-- ── Síntomas ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `sintomas` (
  `id`          INT          NOT NULL AUTO_INCREMENT,
  `descripcion` VARCHAR(255) NOT NULL,
  `equipo_id`   INT          DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `equipo_id` (`equipo_id`),
  CONSTRAINT `sintomas_ibfk_1` FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Nodos del árbol de decisiones ────────────────────────────
-- Cada nodo es una pregunta. Sus opciones apuntan al siguiente nodo
-- o a un resultado (falla). Esto permite que el árbol crezca
-- dinámicamente sin tocar código Python.
CREATE TABLE IF NOT EXISTS `nodos` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `equipo_id`  INT          DEFAULT NULL,   -- sólo raíz tiene equipo_id
  `pregunta`   VARCHAR(400) NOT NULL,
  `es_raiz`    TINYINT(1)   DEFAULT 0,
  `activo`     TINYINT(1)   DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `equipo_id` (`equipo_id`),
  CONSTRAINT `nodos_ibfk_1` FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Fallas ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `fallas` (
  `id`          INT          NOT NULL AUTO_INCREMENT,
  `nombre`      VARCHAR(255) NOT NULL,
  `descripcion` TEXT,
  `severidad`   ENUM('baja','media','alta') DEFAULT 'media',
  `equipos_tag` VARCHAR(200) DEFAULT NULL,
  `veces_diagnosticada` INT DEFAULT 0,
  `veces_correcta`      INT DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Opciones de cada nodo ────────────────────────────────────
CREATE TABLE IF NOT EXISTS `opciones` (
  `id`              INT          NOT NULL AUTO_INCREMENT,
  `nodo_id`         INT          NOT NULL,
  `texto`           VARCHAR(300) NOT NULL,
  `icono`           VARCHAR(10)  DEFAULT NULL,
  `siguiente_nodo`  INT          DEFAULT NULL,  -- NULL si es hoja
  `falla_id`        INT          DEFAULT NULL,  -- solo si es hoja
  `orden`           INT          DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `nodo_id` (`nodo_id`),
  KEY `siguiente_nodo` (`siguiente_nodo`),
  KEY `falla_id` (`falla_id`),
  CONSTRAINT `opciones_ibfk_1` FOREIGN KEY (`nodo_id`)        REFERENCES `nodos`  (`id`),
  CONSTRAINT `opciones_ibfk_2` FOREIGN KEY (`siguiente_nodo`) REFERENCES `nodos`  (`id`),
  CONSTRAINT `opciones_ibfk_3` FOREIGN KEY (`falla_id`)       REFERENCES `fallas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Soluciones ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `soluciones` (
  `id`          INT  NOT NULL AUTO_INCREMENT,
  `descripcion` TEXT,
  `falla_id`    INT  DEFAULT NULL,
  `tags`        VARCHAR(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `falla_id` (`falla_id`),
  CONSTRAINT `soluciones_ibfk_1` FOREIGN KEY (`falla_id`) REFERENCES `fallas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Sesiones de diagnóstico ──────────────────────────────────
-- Registra cada diagnóstico completo para análisis y aprendizaje.
CREATE TABLE IF NOT EXISTS `sesiones` (
  `id`              INT      NOT NULL AUTO_INCREMENT,
  `equipo_id`       INT      DEFAULT NULL,
  `falla_id`        INT      DEFAULT NULL,   -- diagnóstico dado
  `probabilidad`    INT      DEFAULT NULL,
  `camino_json`     JSON     DEFAULT NULL,   -- preguntas/respuestas
  `fue_correcto`    TINYINT(1) DEFAULT NULL, -- NULL = sin feedback aún
  `falla_real_id`   INT      DEFAULT NULL,   -- si el usuario corrigió
  `nota_usuario`    TEXT     DEFAULT NULL,
  `nivel_usuario`   ENUM('tecnico','normal') DEFAULT 'normal',
  `created_at`      DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `equipo_id` (`equipo_id`),
  KEY `falla_id`  (`falla_id`),
  CONSTRAINT `sesiones_ibfk_1` FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`),
  CONSTRAINT `sesiones_ibfk_2` FOREIGN KEY (`falla_id`)  REFERENCES `fallas`  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Correcciones / aprendizaje ───────────────────────────────
-- Cuando un técnico o usuario dice "el diagnóstico estaba mal",
-- se guarda aquí y se ajusta la confianza de la falla.
CREATE TABLE IF NOT EXISTS `correcciones` (
  `id`            INT  NOT NULL AUTO_INCREMENT,
  `sesion_id`     INT  NOT NULL,
  `falla_correcta_id` INT DEFAULT NULL,
  `descripcion_libre` TEXT DEFAULT NULL,   -- si el técnico escribe la falla
  `nivel_usuario` ENUM('tecnico','normal') DEFAULT 'normal',
  `revisado`      TINYINT(1) DEFAULT 0,    -- admin marcó como revisado
  `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `sesion_id` (`sesion_id`),
  CONSTRAINT `correcciones_ibfk_1` FOREIGN KEY (`sesion_id`) REFERENCES `sesiones` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Datos iniciales: Fallas ───────────────────────────────────
INSERT INTO `fallas` (`nombre`, `descripcion`, `severidad`, `equipos_tag`) VALUES
('Fuga de refrigerante',              'Pérdida de gas por fisura o conexión suelta.',            'alta',  'Ref,Cong,AA,EC,CF'),
('Capilar obstruido',                 'Restricción de flujo por suciedad o humedad.',            'media', 'Ref,Cong,EC'),
('Compresor defectuoso',              'Devanado quemado o falla mecánica interna.',              'alta',  'Todos'),
('Relay o capacitor defectuoso',      'Componente de arranque del compresor fallido.',           'media', 'Ref,Cong,AA,EC'),
('Termostato defectuoso',             'Control de temperatura fuera de calibración.',            'media', 'Ref,Cong,EC,CF'),
('Motor ventilador evaporador dañado','Ventilador interno no circula el aire.',                  'media', 'Ref,Cong,EC,CF'),
('Motor ventilador condensador dañado','Ventilador externo no disipa calor.',                   'media', 'AA,EC,CF'),
('Condensador obstruido',             'Acumulación de polvo impide disipación de calor.',        'media', 'Todos'),
('Drenaje obstruido',                 'Tubería de drenaje tapada por algas o suciedad.',         'baja',  'Ref,AA'),
('Empaque de puerta deteriorado',     'Sellado roto permite entrada de aire caliente.',          'baja',  'Ref,Cong,EC,CF'),
('Sistema de deshielo defectuoso',    'Resistencia o temporizador de deshielo fallido.',         'media', 'Ref,Cong,CF'),
('Tarjeta de control dañada',         'PCB con componentes quemados o corroídos.',              'alta',  'AA,EC,CF'),
('Filtros sucios (AA)',               'Filtros de aire obstruidos por polvo.',                   'baja',  'AA'),
('Aislamiento térmico deteriorado',   'Paneles o juntas con pérdida de aislamiento.',            'alta',  'CF'),
('Sensor de temperatura defectuoso',  'Lectura errónea provoca ciclos incorrectos.',             'media', 'AA,EC,CF'),
('Resistencias anti-vaho defectuosas','Cristales con condensación excesiva.',                   'media', 'EC'),
('Falla eléctrica externa',           'Fusible o breaker abierto en instalación.',              'alta',  'Todos'),
('Rodamientos de ventilador desgastados','Vibración y ruido por desgaste mecánico.',            'media', 'Ref,AA,EC')
ON DUPLICATE KEY UPDATE `nombre`=VALUES(`nombre`);

-- ── Soluciones ───────────────────────────────────────────────
INSERT INTO `soluciones` (`falla_id`, `descripcion`, `tags`) VALUES
(1,  'Realizar prueba de presión con nitrógeno. Localizar fuga con detector electrónico. Sellar y recargar.', 'Refrigerante,Urgente'),
(2,  'Verificar capilar con presión de nitrógeno. Sustituir capilar y filtro secador.',                       'Hidráulico,Limpieza'),
(3,  'Medir resistencias del compresor con multímetro. Revisar protector térmico. Reemplazar si necesario.',   'Eléctrico,Compresor'),
(4,  'Reemplazar relay PTC o capacitor de arranque. Verificar valor correcto con multímetro.',                 'Eléctrico,Arranque'),
(5,  'Verificar continuidad del termostato. Calibrar o sustituir.',                                           'Eléctrico,Control'),
(6,  'Revisar motor del ventilador interno. Comprobar rodamientos y alimentación eléctrica.',                  'Mecánico,Ventilación'),
(7,  'Revisar motor del ventilador externo. Verificar voltaje y rodamientos.',                                 'Mecánico,Ventilación'),
(8,  'Limpiar condensador con compresor de aire. Verificar espacio de ventilación alrededor.',                 'Limpieza,Eficiencia'),
(9,  'Limpiar orificio de drenaje con agua caliente o aire comprimido. Aplicar pastilla desinfectante.',       'Hidráulico,Limpieza'),
(10, 'Reemplazar empaque de goma. Verificar alineación y bisagras de puerta.',                                 'Sellado,Fácil'),
(11, 'Descongelar manualmente. Revisar resistencia, temporizador y termostato de deshielo.',                   'Eléctrico,Deshielo'),
(12, 'Diagnóstico electrónico completo. Reemplazar PCB si necesario.',                                         'Electrónico,Control'),
(13, 'Limpiar o reemplazar filtros. Limpiar evaporador con espuma especializada.',                             'Limpieza,Fácil'),
(14, 'Reparar o reemplazar paneles de aislamiento. Sellar juntas con espuma de poliuretano.',                  'Aislamiento,Urgente'),
(15, 'Verificar calibración del sensor con termómetro de referencia. Reemplazar si necesario.',               'Control,Electrónico'),
(16, 'Verificar continuidad de resistencias anti-vaho. Medir voltaje de alimentación.',                        'Eléctrico,Anti-vaho'),
(17, 'Revisar fusibles del tablero. Verificar breaker. Comprobar voltaje en tomacorriente.',                   'Eléctrico,Instalación'),
(18, 'Lubricar o reemplazar motor del ventilador. Verificar desbalance en aspas.',                             'Mecánico,Rodamientos');
