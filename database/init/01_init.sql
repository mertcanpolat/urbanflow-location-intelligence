-- PostgreSQL'e mekânsal veri tipleri ve fonksiyonları ekler.
CREATE EXTENSION IF NOT EXISTS postgis;

-- İleride UUID üretmek için kullanılacaktır.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Veri yaşam döngüsünü ayrı katmanlarda yöneteceğiz.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

COMMENT ON SCHEMA raw IS
    'Kaynaktan geldiği haliyle saklanan ham veriler.';

COMMENT ON SCHEMA staging IS
    'Temizleme, doğrulama ve veri tipi dönüşümlerinin yapıldığı katman.';

COMMENT ON SCHEMA core IS
    'Doğrulanmış, ilişkisel ve mekânsal ana veri modeli.';

COMMENT ON SCHEMA analytics IS
    'API, dashboard ve raporların kullanacağı analitik tablolar.';