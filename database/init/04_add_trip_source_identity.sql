-- Kaynak dosyadaki satırın sırasını saklar.
ALTER TABLE core.trips
ADD COLUMN IF NOT EXISTS source_row_number BIGINT;

-- Tablo henüz boş olduğu için alanı zorunlu hâle getirebiliriz.
ALTER TABLE core.trips
ALTER COLUMN source_row_number SET NOT NULL;

-- Aynı kaynak dosyadaki aynı satır ikinci kez yüklenemez.
CREATE UNIQUE INDEX IF NOT EXISTS uq_trips_source_row
    ON core.trips (source_file, source_row_number);