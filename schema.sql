-- ============================================================
--  FrostAnalitic — Schema v3  (MySQL 8+)
--  Incluye: equipos, síntomas, árbol de decisiones dinámico,
--           fallas, soluciones, sesiones de diagnóstico,
--           sistema de aprendizaje por retroalimentación y
--           usuarios/roles (autenticación).
--
--  Este script es seguro de re-ejecutar sobre una base de datos que
--  ya tenía el schema v2: las tablas nuevas se crean con
--  CREATE TABLE IF NOT EXISTS, y las columnas nuevas en tablas ya
--  existentes se agregan al final con bloques idempotentes
--  (sección "MIGRACIÓN"), que verifican INFORMATION_SCHEMA antes de
--  alterar nada.
-- ============================================================

CREATE DATABASE IF NOT EXISTS `frostanalitic`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `frostanalitic`;

-- ── Equipos ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `equipos` (
  `id`     INT          NOT NULL AUTO_INCREMENT,
  `nombre` VARCHAR(100) NOT NULL,
  `icono`  VARCHAR(10)  DEFAULT '🔧',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_equipos_nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `equipos` (`nombre`, `icono`) VALUES
  ('Refrigerador',      '🧊'),
  ('Congelador',        '🥶'),
  ('Aire Acondicionado','💨'),
  ('Enfriador Comercial','🏪'),
  ('Cuarto Frío',       '🏭')
ON DUPLICATE KEY UPDATE `nombre`=VALUES(`nombre`);

-- ── Usuarios (autenticación y roles) ─────────────────────────
-- rol: 'admin' (edita el árbol y gestiona usuarios), 'tecnico'
-- (ve estadísticas detalladas y exporta reportes), 'normal'
-- (diagnostica y da retroalimentación, igual que un invitado).
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id`            INT          NOT NULL AUTO_INCREMENT,
  `nombre`        VARCHAR(120) NOT NULL,
  `email`         VARCHAR(180) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `rol`           ENUM('admin','tecnico','normal') NOT NULL DEFAULT 'normal',
  `activo`        TINYINT(1)   DEFAULT 1,
  `created_at`    DATETIME     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fallas_nombre` (`nombre`)
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
  `prob_experto`    INT          DEFAULT NULL,  -- % estimado por el experto (solo si es hoja)
  `rec_text`        TEXT         DEFAULT NULL,  -- recomendación específica de este camino (solo si es hoja)
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
  `usuario_id`      INT      DEFAULT NULL,   -- quién lo ejecutó (NULL = invitado anónimo)
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
  KEY `usuario_id` (`usuario_id`),
  CONSTRAINT `sesiones_ibfk_1` FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`),
  CONSTRAINT `sesiones_ibfk_2` FOREIGN KEY (`falla_id`)  REFERENCES `fallas`  (`id`),
  CONSTRAINT `sesiones_ibfk_3` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
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
(18, 'Lubricar o reemplazar motor del ventilador. Verificar desbalance en aspas.',                             'Mecánico,Rodamientos')
ON DUPLICATE KEY UPDATE `tags`=VALUES(`tags`);

-- ============================================================
--  MIGRACIÓN IDEMPOTENTE (schema v2 -> v3)
--  Si esta base de datos ya existía con el schema v2 (antes de
--  usuarios/roles y del árbol dinámico con prob_experto/rec_text),
--  las tablas de arriba ya estaban creadas SIN estas columnas
--  nuevas, y CREATE TABLE IF NOT EXISTS no las agrega. Estos
--  bloques verifican INFORMATION_SCHEMA y solo alteran la tabla si
--  hace falta, así que es seguro correr este archivo completo
--  las veces que quieras, tanto en una BD nueva como en una vieja.
-- ============================================================

-- `opciones`.prob_experto
SET @col_existe = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'opciones' AND COLUMN_NAME = 'prob_experto');
SET @sql = IF(@col_existe = 0,
  'ALTER TABLE `opciones` ADD COLUMN `prob_experto` INT DEFAULT NULL',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- `opciones`.rec_text
SET @col_existe = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'opciones' AND COLUMN_NAME = 'rec_text');
SET @sql = IF(@col_existe = 0,
  'ALTER TABLE `opciones` ADD COLUMN `rec_text` TEXT DEFAULT NULL',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- `sesiones`.usuario_id (+ FK a usuarios)
SET @col_existe = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'sesiones' AND COLUMN_NAME = 'usuario_id');
SET @sql = IF(@col_existe = 0,
  'ALTER TABLE `sesiones` ADD COLUMN `usuario_id` INT DEFAULT NULL, ADD KEY `usuario_id` (`usuario_id`), ADD CONSTRAINT `sesiones_ibfk_3` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
--  MIGRACIÓN IDEMPOTENTE (schema v3 -> v3.1)
--  Bug corregido: los INSERT de `equipos` y `fallas` de más arriba
--  usaban "ON DUPLICATE KEY UPDATE" pero ninguna de las dos tablas
--  tenía una UNIQUE KEY en `nombre` que lo hiciera funcionar, así que
--  cada vez que se volvía a correr schema.sql (algo que este mismo
--  proyecto ha necesitado hacer varias veces) se insertaban de nuevo
--  los 5 equipos y las 18 fallas "de fábrica" como filas duplicadas.
--  Esto se ve, por ejemplo, como tarjetas de equipo repetidas en
--  "Acceso rápido".
--
--  Los bloques de abajo son seguros de correr las veces que quieras:
--  1) Fusionan cualquier duplicado que ya exista (reasignando primero
--     las referencias de otras tablas al registro más antiguo).
--  2) Agregan la UNIQUE KEY que faltaba, así que a partir de ahora un
--     futuro re-run de este archivo ya no vuelve a duplicar nada.
-- ============================================================

-- Fusionar equipos duplicados (mismo nombre) hacia el de menor id.
UPDATE `nodos` n
  JOIN `equipos` dup ON n.equipo_id = dup.id
  JOIN `equipos` ok  ON ok.nombre = dup.nombre AND ok.id < dup.id
  SET n.equipo_id = ok.id;

UPDATE `sesiones` s
  JOIN `equipos` dup ON s.equipo_id = dup.id
  JOIN `equipos` ok  ON ok.nombre = dup.nombre AND ok.id < dup.id
  SET s.equipo_id = ok.id;

DELETE dup FROM `equipos` dup
  JOIN `equipos` ok ON ok.nombre = dup.nombre AND ok.id < dup.id;

-- `equipos`.UNIQUE(nombre) — solo si todavía no existe
SET @idx_existe = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipos' AND INDEX_NAME = 'uq_equipos_nombre');
SET @sql = IF(@idx_existe = 0,
  'ALTER TABLE `equipos` ADD UNIQUE KEY `uq_equipos_nombre` (`nombre`)',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Fusionar fallas duplicadas (mismo nombre) hacia la de menor id,
-- sumando primero sus contadores de uso real para no perder historial.
UPDATE `fallas` ok
  JOIN (
    SELECT ok2.id AS ok_id,
           SUM(dup2.veces_diagnosticada) AS suma_diag,
           SUM(dup2.veces_correcta)      AS suma_correcta
    FROM `fallas` dup2
    JOIN `fallas` ok2 ON ok2.nombre = dup2.nombre AND ok2.id < dup2.id
    GROUP BY ok2.id
  ) t ON t.ok_id = ok.id
  SET ok.veces_diagnosticada = ok.veces_diagnosticada + t.suma_diag,
      ok.veces_correcta      = ok.veces_correcta + t.suma_correcta;

UPDATE `opciones` o
  JOIN `fallas` dup ON o.falla_id = dup.id
  JOIN `fallas` ok  ON ok.nombre = dup.nombre AND ok.id < dup.id
  SET o.falla_id = ok.id;

UPDATE `sesiones` s
  JOIN `fallas` dup ON s.falla_id = dup.id
  JOIN `fallas` ok  ON ok.nombre = dup.nombre AND ok.id < dup.id
  SET s.falla_id = ok.id;

UPDATE `sesiones` s
  JOIN `fallas` dup ON s.falla_real_id = dup.id
  JOIN `fallas` ok  ON ok.nombre = dup.nombre AND ok.id < dup.id
  SET s.falla_real_id = ok.id;

UPDATE `correcciones` c
  JOIN `fallas` dup ON c.falla_correcta_id = dup.id
  JOIN `fallas` ok  ON ok.nombre = dup.nombre AND ok.id < dup.id
  SET c.falla_correcta_id = ok.id;

UPDATE `soluciones` so
  JOIN `fallas` dup ON so.falla_id = dup.id
  JOIN `fallas` ok  ON ok.nombre = dup.nombre AND ok.id < dup.id
  SET so.falla_id = ok.id;

DELETE dup FROM `fallas` dup
  JOIN `fallas` ok ON ok.nombre = dup.nombre AND ok.id < dup.id;

-- `fallas`.UNIQUE(nombre) — solo si todavía no existe
SET @idx_existe = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'fallas' AND INDEX_NAME = 'uq_fallas_nombre');
SET @sql = IF(@idx_existe = 0,
  'ALTER TABLE `fallas` ADD UNIQUE KEY `uq_fallas_nombre` (`nombre`)',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- `soluciones`: el INSERT de "Datos iniciales" de más arriba no tenía
-- ningún ON DUPLICATE KEY (ni una UNIQUE KEY sobre la que apoyarse), así
-- que cada re-run también dejaba soluciones repetidas para la misma
-- falla. Se limpian los duplicados exactos y se agrega la UNIQUE KEY
-- (con un prefijo de la descripción, porque es un campo TEXT) para que
-- no vuelva a pasar.
DELETE dup FROM `soluciones` dup
  JOIN `soluciones` ok
    ON ok.falla_id = dup.falla_id
   AND ok.descripcion = dup.descripcion
   AND ok.id < dup.id;

SET @idx_existe = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'soluciones' AND INDEX_NAME = 'uq_soluciones_falla_desc');
SET @sql = IF(@idx_existe = 0,
  'ALTER TABLE `soluciones` ADD UNIQUE KEY `uq_soluciones_falla_desc` (`falla_id`, `descripcion`(191))',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

