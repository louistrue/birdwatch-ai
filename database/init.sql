-- Bird Watcher Database Schema
-- PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Visual detections from camera + classifier
CREATE TABLE IF NOT EXISTS visual_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    image_path TEXT NOT NULL,
    species VARCHAR(255) NOT NULL,
    common_name VARCHAR(255),
    scientific_name VARCHAR(255),
    confidence FLOAT NOT NULL,
    source VARCHAR(50) DEFAULT 'classifier',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audio detections from BirdNET
CREATE TABLE IF NOT EXISTS audio_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    audio_path TEXT,
    species VARCHAR(255) NOT NULL,
    common_name VARCHAR(255),
    scientific_name VARCHAR(255),
    confidence FLOAT NOT NULL,
    source VARCHAR(50) DEFAULT 'birdnet',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Correlated sightings (visual + audio match)
CREATE TABLE IF NOT EXISTS correlated_sightings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    species VARCHAR(255) NOT NULL,
    common_name VARCHAR(255),
    scientific_name VARCHAR(255),
    confidence FLOAT NOT NULL,
    visual_confidence FLOAT,
    audio_confidence FLOAT,
    image_path TEXT,
    audio_path TEXT,
    time_diff FLOAT,  -- seconds between visual and audio detection
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Species information
CREATE TABLE IF NOT EXISTS species (
    id SERIAL PRIMARY KEY,
    scientific_name VARCHAR(255) UNIQUE NOT NULL,
    common_name_en VARCHAR(255),
    common_name_de VARCHAR(255),  -- Swiss German names
    common_name_fr VARCHAR(255),  -- Swiss French names
    family VARCHAR(255),
    conservation_status VARCHAR(50),
    typical_habitat TEXT,
    migration_pattern VARCHAR(50),
    swiss_resident BOOLEAN DEFAULT TRUE,
    image_url TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Daily statistics
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    species VARCHAR(255) NOT NULL,
    visual_count INTEGER DEFAULT 0,
    audio_count INTEGER DEFAULT 0,
    correlated_count INTEGER DEFAULT 0,
    first_seen TIME,
    last_seen TIME,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, species)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_visual_timestamp ON visual_detections(timestamp);
CREATE INDEX IF NOT EXISTS idx_visual_species ON visual_detections(species);
CREATE INDEX IF NOT EXISTS idx_audio_timestamp ON audio_detections(timestamp);
CREATE INDEX IF NOT EXISTS idx_audio_species ON audio_detections(species);
CREATE INDEX IF NOT EXISTS idx_correlated_timestamp ON correlated_sightings(timestamp);
CREATE INDEX IF NOT EXISTS idx_correlated_species ON correlated_sightings(species);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);

-- Insert common Swiss garden bird species
INSERT INTO species (scientific_name, common_name_en, common_name_de, family, swiss_resident) VALUES
    ('Parus major', 'Great Tit', 'Kohlmeise', 'Paridae', TRUE),
    ('Cyanistes caeruleus', 'Eurasian Blue Tit', 'Blaumeise', 'Paridae', TRUE),
    ('Passer domesticus', 'House Sparrow', 'Haussperling', 'Passeridae', TRUE),
    ('Turdus merula', 'Common Blackbird', 'Amsel', 'Turdidae', TRUE),
    ('Erithacus rubecula', 'European Robin', 'Rotkehlchen', 'Muscicapidae', TRUE),
    ('Fringilla coelebs', 'Common Chaffinch', 'Buchfink', 'Fringillidae', TRUE),
    ('Chloris chloris', 'European Greenfinch', 'Grünfink', 'Fringillidae', TRUE),
    ('Pica pica', 'Eurasian Magpie', 'Elster', 'Corvidae', TRUE),
    ('Columba palumbus', 'Common Wood Pigeon', 'Ringeltaube', 'Columbidae', TRUE),
    ('Dendrocopos major', 'Great Spotted Woodpecker', 'Buntspecht', 'Picidae', TRUE),
    ('Sturnus vulgaris', 'European Starling', 'Star', 'Sturnidae', TRUE),
    ('Carduelis carduelis', 'European Goldfinch', 'Stieglitz', 'Fringillidae', TRUE),
    ('Phylloscopus collybita', 'Common Chiffchaff', 'Zilpzalp', 'Phylloscopidae', TRUE),
    ('Sitta europaea', 'Eurasian Nuthatch', 'Kleiber', 'Sittidae', TRUE),
    ('Troglodytes troglodytes', 'Eurasian Wren', 'Zaunkönig', 'Troglodytidae', TRUE)
ON CONFLICT (scientific_name) DO NOTHING;

-- Function to update daily stats
CREATE OR REPLACE FUNCTION update_daily_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO daily_stats (date, species, visual_count, audio_count, correlated_count)
    VALUES (
        CURRENT_DATE,
        NEW.species,
        CASE WHEN TG_TABLE_NAME = 'visual_detections' THEN 1 ELSE 0 END,
        CASE WHEN TG_TABLE_NAME = 'audio_detections' THEN 1 ELSE 0 END,
        CASE WHEN TG_TABLE_NAME = 'correlated_sightings' THEN 1 ELSE 0 END
    )
    ON CONFLICT (date, species) DO UPDATE SET
        visual_count = daily_stats.visual_count + CASE WHEN TG_TABLE_NAME = 'visual_detections' THEN 1 ELSE 0 END,
        audio_count = daily_stats.audio_count + CASE WHEN TG_TABLE_NAME = 'audio_detections' THEN 1 ELSE 0 END,
        correlated_count = daily_stats.correlated_count + CASE WHEN TG_TABLE_NAME = 'correlated_sightings' THEN 1 ELSE 0 END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic stats updates
CREATE TRIGGER visual_detection_stats
    AFTER INSERT ON visual_detections
    FOR EACH ROW EXECUTE FUNCTION update_daily_stats();

CREATE TRIGGER audio_detection_stats
    AFTER INSERT ON audio_detections
    FOR EACH ROW EXECUTE FUNCTION update_daily_stats();

CREATE TRIGGER correlated_sighting_stats
    AFTER INSERT ON correlated_sightings
    FOR EACH ROW EXECUTE FUNCTION update_daily_stats();

-- View for combined detections
CREATE OR REPLACE VIEW all_detections AS
SELECT
    'visual' AS source,
    id,
    timestamp,
    species,
    common_name,
    confidence,
    image_path AS media_path,
    NULL AS audio_path
FROM visual_detections
UNION ALL
SELECT
    'audio' AS source,
    id,
    timestamp,
    species,
    common_name,
    confidence,
    NULL AS media_path,
    audio_path
FROM audio_detections
UNION ALL
SELECT
    'correlated' AS source,
    id,
    timestamp,
    species,
    common_name,
    confidence,
    image_path AS media_path,
    audio_path
FROM correlated_sightings
ORDER BY timestamp DESC;

-- View for today's activity
CREATE OR REPLACE VIEW todays_sightings AS
SELECT
    species,
    common_name,
    COUNT(*) AS total_count,
    MAX(confidence) AS max_confidence,
    MIN(timestamp) AS first_seen,
    MAX(timestamp) AS last_seen
FROM all_detections
WHERE timestamp >= CURRENT_DATE
GROUP BY species, common_name
ORDER BY total_count DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO birdwatch;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO birdwatch;
