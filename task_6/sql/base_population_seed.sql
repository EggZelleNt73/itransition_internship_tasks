-- ENG Lookups
INSERT INTO faker.lookup_first_names (locale, gender, first_name, seq_id) VALUES
('ENG', 'M', 'John', 1), ('ENG', 'M', 'Robert', 2), ('ENG', 'M', 'Michael', 3),
('ENG', 'F', 'Mary', 1), ('ENG', 'F', 'Patricia', 2), ('ENG', 'F', 'Jennifer', 3);

INSERT INTO faker.lookup_last_names (locale, last_name, seq_id) VALUES
('ENG', 'Smith', 1), ('ENG', 'Johnson', 2), ('ENG', 'Williams', 3);

INSERT INTO faker.lookup_streets (locale, street_name, seq_id) VALUES
('ENG', 'Main Street', 1), ('ENG', 'Oak Avenue', 2), ('ENG', 'Pine Road', 3);

INSERT INTO faker.lookup_cities (locale, city_name, state_or_region, postal_code_pattern, seq_id) VALUES
('ENG', 'New York', 'NY', '#####', 1), ('ENG', 'Los Angeles', 'CA', '#####', 2);

-- DEU Lookups
INSERT INTO faker.lookup_first_names (locale, gender, first_name, seq_id) VALUES
('DEU', 'M', 'Hans', 1), ('DEU', 'M', 'Lucas', 2), ('DEU', 'M', 'Wolfgang', 3),
('DEU', 'F', 'Anna', 1), ('DEU', 'F', 'Maria', 2), ('DEU', 'F', 'Laura', 3);

INSERT INTO faker.lookup_last_names (locale, last_name, seq_id) VALUES
('DEU', 'Müller', 1), ('DEU', 'Schmidt', 2), ('DEU', 'Schneider', 3);

INSERT INTO faker.lookup_streets (locale, street_name, seq_id) VALUES
('DEU', 'Hauptstraße', 1), ('DEU', 'Goethestraße', 2), ('DEU', 'Biberweg', 3);

INSERT INTO faker.lookup_cities (locale, city_name, state_or_region, postal_code_pattern, seq_id) VALUES
('DEU', 'Berlin', 'BE', '#####', 1), ('DEU', 'München', 'BY', '#####', 2);
