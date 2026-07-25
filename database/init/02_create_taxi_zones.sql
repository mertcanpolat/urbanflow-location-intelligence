-- ============================================================
-- NYC Taxi Zones ana tablosu
-- ============================================================

CREATE TABLE IF NOT EXISTS core.taxi_zones (
    location_id SMALLINT PRIMARY KEY,
    zone_name VARCHAR(150) NOT NULL,
    borough VARCHAR(50) NOT NULL,
    service_zone VARCHAR(50),
    geom geometry(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE core.taxi_zones IS
    'NYC TLC taksi bölgelerinin doğrulanmış ana mekânsal tablosu.';

COMMENT ON COLUMN core.taxi_zones.location_id IS
    'TLC yolculuk kayıtlarında kullanılan benzersiz taksi bölgesi kimliği.';

COMMENT ON COLUMN core.taxi_zones.zone_name IS
    'Taksi bölgesinin açıklayıcı adı.';

COMMENT ON COLUMN core.taxi_zones.borough IS
    'Bölgenin bağlı olduğu New York borough bilgisi.';

COMMENT ON COLUMN core.taxi_zones.service_zone IS
    'Yellow Zone, Boro Zone veya Airports gibi hizmet sınıfı.';

COMMENT ON COLUMN core.taxi_zones.geom IS
    'EPSG:4326 koordinat sisteminde MultiPolygon taksi bölgesi geometrisi.';

CREATE INDEX IF NOT EXISTS idx_taxi_zones_geom
    ON core.taxi_zones
    USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_taxi_zones_borough
    ON core.taxi_zones (borough);