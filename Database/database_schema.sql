-- Enable PostGIS for GEOGRAPHY(Point,4326)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Document table
CREATE TABLE Document (
    document_id SERIAL PRIMARY KEY,
    document_name VARCHAR(255),
    document_url VARCHAR(255)
);

-- Sample table
CREATE TABLE Sample (
    id SERIAL PRIMARY KEY,
    sample_name VARCHAR(255),
    sample_image_url VARCHAR(255),
    description VARCHAR(500),
    origin GEOGRAPHY(Point, 4326),
    date_collected TIMESTAMP
);

-- Equipment table
CREATE TABLE Equipment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(255)
);

-- SampleImage table
CREATE TABLE SampleImage (
    id SERIAL PRIMARY KEY,
    image_url VARCHAR(255),
    caption VARCHAR(255),
    date_obtained TIMESTAMP,
    sample_id INT REFERENCES Sample(id) ON DELETE CASCADE,
    equipment_id INT REFERENCES Equipment(id) ON DELETE SET NULL
);

-- References table (junction between Sample and Document)
CREATE TABLE "References" (
    id SERIAL PRIMARY KEY,
    sample_id INT REFERENCES Sample(id) ON DELETE CASCADE,
    document_id INT REFERENCES Document(document_id) ON DELETE CASCADE
);
