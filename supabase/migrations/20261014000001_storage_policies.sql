-- =====================================================================
-- Políticas de Seguridad RLS para el Bucket IMG_perfumes (Supabase Storage)
-- =====================================================================
-- Permite lectura pública, subida y actualización de imágenes de perfumes.

-- 1. Permitir lectura y descarga pública de cualquier imagen del bucket
DROP POLICY IF EXISTS "Permitir lectura publica IMG_perfumes" ON storage.objects;
CREATE POLICY "Permitir lectura publica IMG_perfumes"
ON storage.objects FOR SELECT
USING (bucket_id = 'IMG_perfumes');

-- 2. Permitir inserción/subida de imágenes al bucket
DROP POLICY IF EXISTS "Permitir subida IMG_perfumes" ON storage.objects;
CREATE POLICY "Permitir subida IMG_perfumes"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'IMG_perfumes');

-- 3. Permitir actualización/reemplazo de imágenes
DROP POLICY IF EXISTS "Permitir actualizacion IMG_perfumes" ON storage.objects;
CREATE POLICY "Permitir actualizacion IMG_perfumes"
ON storage.objects FOR UPDATE
USING (bucket_id = 'IMG_perfumes');

-- 4. Permitir eliminación
DROP POLICY IF EXISTS "Permitir borrado IMG_perfumes" ON storage.objects;
CREATE POLICY "Permitir borrado IMG_perfumes"
ON storage.objects FOR DELETE
USING (bucket_id = 'IMG_perfumes');
