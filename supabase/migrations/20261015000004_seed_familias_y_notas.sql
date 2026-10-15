-- =====================================================================
-- PerfumeTrending.cl — Migración 20261015000004
-- Seed Idempotente: 12 Familias y 107 Notas Olfativas Canónicas
-- + 10 Familias Olfativas Generales
-- =====================================================================

BEGIN;

-- 1. Familias de Notas (12 categorías oficiales)
INSERT INTO public.familias_notas (slug, nombre, emoji, descripcion, orden) VALUES
('citricos-hesperides', 'Cítricos & Hespérides', '🍋', 'Notas cítricas frescas y revitalizantes.', 1),
('frutales-bayas', 'Frutales & Bayas', '🍎', 'Frutas jugosas, bayas y acordes pulposos.', 2),
('florales-clasicos-nobles', 'Florales Clásicos & Nobles', '🌸', 'Flores tradicionales de alta perfumería.', 3),
('flores-blancas-solares', 'Flores Blancas & Solares', '🌼', 'Flores luminosas, narcóticas y cremosas.', 4),
('herbales-aromaticos-verdes', 'Herbales, Aromáticos & Verdes', '🌿', 'Hierbas frescas, follaje y acordes silvestres.', 5),
('especias-calidas-frescas', 'Especias Cálidas & Frescas', '🌶️', 'Especias picantes, aromáticas y exóticas.', 6),
('gourmand-dulces', 'Gourmand & Dulces Adictivos', '🍫', 'Acordes apetitosos de repostería, café y chocolate.', 7),
('maderas-nobles', 'Maderas Nobles', '🌲', 'Troncos, raíces y cortezas de carácter elegante.', 8),
('resinas-balsamicos', 'Resinas & Balsámicos', '🏺', 'Bálsamos sagrados, gomas y exudados ambarinos.', 9),
('almizcles-animalicos', 'Almizcles & Notas Animalic', '🦌', 'Fijadores sensuales, almizcles y calidez de piel.', 10),
('licorosas-bebidas', 'Licorosas & Bebidas', '🥃', 'Destilados nobles, cócteles y acordes espirituosos.', 11),
('moleculas-cuero-vanguardia', 'Moléculas Modernas, Cuero & Vanguardia', '🧪', 'Sintéticos limpios, cuero curtido y acordes conceptuales.', 12)
ON CONFLICT (slug) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    emoji = EXCLUDED.emoji,
    orden = EXCLUDED.orden,
    descripcion = COALESCE(public.familias_notas.descripcion, EXCLUDED.descripcion);

-- 2. 107 Notas Olfativas Canónicas
WITH d(familia_slug, slug, nombre, sinonimos) AS (VALUES
-- 1 Cítricos (9)
('citricos-hesperides', 'bergamota', 'Bergamota', ARRAY[]::text[]),
('citricos-hesperides', 'clementina', 'Clementina', ARRAY[]::text[]),
('citricos-hesperides', 'lima', 'Lima', ARRAY[]::text[]),
('citricos-hesperides', 'limon', 'Limón', ARRAY['limón amarillo']),
('citricos-hesperides', 'mandarina', 'Mandarina', ARRAY[]::text[]),
('citricos-hesperides', 'neroli', 'Neroli', ARRAY['néroli']),
('citricos-hesperides', 'petit-grain', 'Petit Grain', ARRAY['petitgrain']),
('citricos-hesperides', 'pomelo-toronja', 'Pomelo (Toronja)', ARRAY['pomelo','toronja']),
('citricos-hesperides', 'yuzu', 'Yuzu', ARRAY[]::text[]),

-- 2 Frutales (15)
('frutales-bayas', 'almendra', 'Almendra', ARRAY[]::text[]),
('frutales-bayas', 'avellana', 'Avellana', ARRAY[]::text[]),
('frutales-bayas', 'ciruela', 'Ciruela', ARRAY[]::text[]),
('frutales-bayas', 'coco', 'Coco', ARRAY[]::text[]),
('frutales-bayas', 'durazno-melocoton', 'Durazno (Melocotón)', ARRAY['durazno','melocotón','melocoton']),
('frutales-bayas', 'frambuesa', 'Frambuesa', ARRAY[]::text[]),
('frutales-bayas', 'grosellas-negras', 'Grosellas Negras', ARRAY['grosella negra','blackcurrant','cassis']),
('frutales-bayas', 'higo', 'Higo', ARRAY[]::text[]),
('frutales-bayas', 'lichi', 'Lichi', ARRAY['litchi','lychee']),
('frutales-bayas', 'manzana', 'Manzana', ARRAY[]::text[]),
('frutales-bayas', 'melon', 'Melón', ARRAY['melón']),
('frutales-bayas', 'pera', 'Pera', ARRAY[]::text[]),
('frutales-bayas', 'pina', 'Piña', ARRAY['piña','ananá','anana']),
('frutales-bayas', 'ruibarbo', 'Ruibarbo', ARRAY[]::text[]),
('frutales-bayas', 'sandia', 'Sandía', ARRAY['sandía']),

-- 3 Florales clásicos (10)
('florales-clasicos-nobles', 'fresia', 'Fresia', ARRAY['freesia']),
('florales-clasicos-nobles', 'geranio', 'Geranio', ARRAY[]::text[]),
('florales-clasicos-nobles', 'heliotropo', 'Heliotropo', ARRAY[]::text[]),
('florales-clasicos-nobles', 'iris-orris', 'Iris (Orris)', ARRAY['orris','raíz de iris']),
('florales-clasicos-nobles', 'lavanda', 'Lavanda', ARRAY['lavender']),
('florales-clasicos-nobles', 'lilium-lirio', 'Lilium (Lirio)', ARRAY['lilium','lirio']),
('florales-clasicos-nobles', 'mimosa', 'Mimosa', ARRAY[]::text[]),
('florales-clasicos-nobles', 'peonia', 'Peonía', ARRAY['peonía']),
('florales-clasicos-nobles', 'rosa', 'Rosa', ARRAY[]::text[]),
('florales-clasicos-nobles', 'violeta', 'Violeta', ARRAY[]::text[]),

-- 4 Flores blancas (7)
('flores-blancas-solares', 'flor-azahar-naranjo', 'Flor de Azahar del Naranjo', ARRAY['azahar','orange blossom']),
('flores-blancas-solares', 'flor-frangipani', 'Flor de Frangipani', ARRAY['frangipani','plumeria']),
('flores-blancas-solares', 'gardenia', 'Gardenia', ARRAY[]::text[]),
('flores-blancas-solares', 'jazmin', 'Jazmín', ARRAY['jasmine']),
('flores-blancas-solares', 'magnolia', 'Magnolia', ARRAY[]::text[]),
('flores-blancas-solares', 'tuberosa-nardo', 'Tuberosa (Nardo)', ARRAY['tuberosa','nardo','tuberose']),
('flores-blancas-solares', 'ylang-ylang', 'Ylang-Ylang', ARRAY['ylang ylang']),

-- 5 Herbales (13)
('herbales-aromaticos-verdes', 'abedul', 'Abedul', ARRAY['birch']),
('herbales-aromaticos-verdes', 'albahaca', 'Albahaca', ARRAY['basil']),
('herbales-aromaticos-verdes', 'eucalipto', 'Eucalipto', ARRAY['eucalyptus']),
('herbales-aromaticos-verdes', 'galbano', 'Gálbano', ARRAY['galbanum']),
('herbales-aromaticos-verdes', 'hojas-violeta', 'Hojas de Violeta', ARRAY['violet leaf']),
('herbales-aromaticos-verdes', 'menta', 'Menta', ARRAY['mint']),
('herbales-aromaticos-verdes', 'pachuli', 'Pachulí', ARRAY['patchouli']),
('herbales-aromaticos-verdes', 'romero', 'Romero', ARRAY['rosemary']),
('herbales-aromaticos-verdes', 'salvia', 'Salvia', ARRAY['sage']),
('herbales-aromaticos-verdes', 'te-blanco', 'Té Blanco', ARRAY['white tea']),
('herbales-aromaticos-verdes', 'te-negro', 'Té Negro', ARRAY['black tea']),
('herbales-aromaticos-verdes', 'te-verde', 'Té Verde', ARRAY['green tea']),
('herbales-aromaticos-verdes', 'vetiver', 'Vetiver', ARRAY[]::text[]),

-- 6 Especias (10)
('especias-calidas-frescas', 'anis-estrellado', 'Anís Estrellado', ARRAY['star anise']),
('especias-calidas-frescas', 'azafran', 'Azafrán', ARRAY['saffron']),
('especias-calidas-frescas', 'canela', 'Canela', ARRAY['cinnamon']),
('especias-calidas-frescas', 'cardamomo', 'Cardamomo', ARRAY['cardamom']),
('especias-calidas-frescas', 'clavo-olor', 'Clavo de Olor', ARRAY['clove']),
('especias-calidas-frescas', 'jengibre', 'Jengibre', ARRAY['ginger']),
('especias-calidas-frescas', 'nuez-moscada', 'Nuez Moscada', ARRAY['nutmeg']),
('especias-calidas-frescas', 'pimienta-blanca', 'Pimienta Blanca', ARRAY['white pepper']),
('especias-calidas-frescas', 'pimienta-negra', 'Pimienta Negra', ARRAY['black pepper']),
('especias-calidas-frescas', 'pimienta-rosa', 'Pimienta Rosa', ARRAY['pink pepper']),

-- 7 Gourmand (9)
('gourmand-dulces', 'cacao-chocolate', 'Cacao / Chocolate', ARRAY['cacao','chocolate']),
('gourmand-dulces', 'cafe', 'Café', ARRAY['coffee']),
('gourmand-dulces', 'caramelo', 'Caramelo', ARRAY['caramel']),
('gourmand-dulces', 'haba-tonka', 'Haba Tonka', ARRAY['tonka bean']),
('gourmand-dulces', 'leche', 'Leche', ARRAY['milk']),
('gourmand-dulces', 'malvavisco', 'Malvavisco', ARRAY['marshmallow']),
('gourmand-dulces', 'miel', 'Miel', ARRAY['honey']),
('gourmand-dulces', 'praline', 'Praliné', ARRAY['praline']),
('gourmand-dulces', 'vainilla', 'Vainilla', ARRAY['vanilla']),

-- 8 Maderas (7)
('maderas-nobles', 'cedro', 'Cedro', ARRAY['cedar']),
('maderas-nobles', 'cipres', 'Ciprés', ARRAY['cypress']),
('maderas-nobles', 'ebano', 'Ébano', ARRAY['ebony']),
('maderas-nobles', 'guayac', 'Guayac', ARRAY[]::text[]),
('maderas-nobles', 'musgo-roble', 'Musgo de Roble', ARRAY['oakmoss']),
('maderas-nobles', 'oud-madera-agar', 'Oud (Madera de Agar)', ARRAY['oud','agarwood']),
('maderas-nobles', 'santalo', 'Sándalo', ARRAY['sandalwood']),

-- 9 Resinas (7)
('resinas-balsamicos', 'ambar-calido', 'Ámbar (Cálido)', ARRAY['amber']),
('resinas-balsamicos', 'balsamo-peru', 'Bálsamo del Perú', ARRAY['peru balsam']),
('resinas-balsamicos', 'benjui', 'Benjuí', ARRAY['benzoin']),
('resinas-balsamicos', 'estoraque', 'Estoraque', ARRAY['storax']),
('resinas-balsamicos', 'incienso-olibano', 'Incienso (Olíbano)', ARRAY['olibanum','frankincense']),
('resinas-balsamicos', 'ladano', 'Ládano', ARRAY['labdanum']),
('resinas-balsamicos', 'mirra', 'Mirra', ARRAY['myrrh']),

-- 10 Almizcles (5)
('almizcles-animalicos', 'almizcle-blanco-musk', 'Almizcle (Blanco/Musk)', ARRAY['white musk','musk']),
('almizcles-animalicos', 'almizcle-vegetal', 'Almizcle Vegetal', ARRAY['plant musk']),
('almizcles-animalicos', 'ambar-gris', 'Ámbar Gris', ARRAY['ambergris']),
('almizcles-animalicos', 'castoreo', 'Castóreo', ARRAY['castoreum']),
('almizcles-animalicos', 'civeta', 'Civeta', ARRAY['civet']),

-- 11 Licorosas (7)
('licorosas-bebidas', 'amaretto', 'Amaretto', ARRAY[]::text[]),
('licorosas-bebidas', 'champan', 'Champán', ARRAY['champagne']),
('licorosas-bebidas', 'cognac', 'Cognac', ARRAY['coñac']),
('licorosas-bebidas', 'ginebra', 'Ginebra', ARRAY['gin']),
('licorosas-bebidas', 'mojito', 'Mojito', ARRAY[]::text[]),
('licorosas-bebidas', 'ron', 'Ron', ARRAY['rum']),
('licorosas-bebidas', 'whisky', 'Whisky', ARRAY['whiskey']),

-- 12 Moléculas y cuero (8)
('moleculas-cuero-vanguardia', 'aldehidos', 'Aldehídos', ARRAY['aldehydes']),
('moleculas-cuero-vanguardia', 'ambroxan', 'Ambroxan', ARRAY[]::text[]),
('moleculas-cuero-vanguardia', 'cashmeran', 'Cachemira (Cashmeran)', ARRAY['cashmeran','cachemira']),
('moleculas-cuero-vanguardia', 'cuero', 'Cuero', ARRAY['leather']),
('moleculas-cuero-vanguardia', 'iso-e-super', 'Iso E Super', ARRAY[]::text[]),
('moleculas-cuero-vanguardia', 'notas-marinas', 'Notas Marinas', ARRAY['marine notes']),
('moleculas-cuero-vanguardia', 'notas-solares', 'Notas Solares', ARRAY['solar notes']),
('moleculas-cuero-vanguardia', 'sangre-metalica', 'Sangre (Metálica)', ARRAY['metallic notes'])
)
INSERT INTO public.notas_olfativas (familia_id, slug, nombre, sinonimos)
SELECT f.id, d.slug, d.nombre, d.sinonimos
FROM d JOIN public.familias_notas f ON f.slug = d.familia_slug
ON CONFLICT (slug) DO UPDATE SET
    familia_id = EXCLUDED.familia_id,
    nombre = EXCLUDED.nombre,
    sinonimos = (
        SELECT ARRAY(
            SELECT DISTINCT x
            FROM unnest(public.notas_olfativas.sinonimos || EXCLUDED.sinonimos) AS u(x)
            WHERE x IS NOT NULL AND length(trim(x)) > 0
            ORDER BY x
        )
    );

-- 3. Familias Olfativas Generales (10 Categorías Editoriales)
INSERT INTO public.familias_olfativas (slug, nombre, descripcion) VALUES
('citrica', 'Cítrica', 'Familia con carácter cítrico predominante.'),
('floral', 'Floral', 'Familia con carácter floral predominante.'),
('amaderada', 'Amaderada', 'Familia con carácter amaderado predominante.'),
('ambar', 'Ámbar', 'Familia cálida y resinosa según clasificación editorial.'),
('aromatica-fougere', 'Aromática / Fougère', 'Familia aromática o fougère.'),
('chipre', 'Chipre', 'Familia chipre.'),
('cuero', 'Cuero', 'Familia con carácter de cuero.'),
('gourmand', 'Gourmand', 'Familia dulce o comestible.'),
('acuatica-marina', 'Acuática / Marina', 'Familia acuática o marina.'),
('verde', 'Verde', 'Familia con carácter verde predominante.')
ON CONFLICT (slug) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = COALESCE(public.familias_olfativas.descripcion, EXCLUDED.descripcion);

COMMIT;
