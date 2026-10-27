CREATE TABLE faker.lookup_first_names (
    id SERIAL PRIMARY KEY,
	locale CHAR(3) NOT NULL,
	gender CHAR(1) NOT NULL,
	first_name VARCHAR(100) NOT NULL,
	seq_id INT NOT NULL,
	CONSTRAINT uq_fn_locale_seq UNIQUE (locale, gender, seq_id)
);


CREATE TABLE faker.lookup_last_names (
    id SERIAL PRIMARY KEY,
	locale CHAR(3) NOT NULL,
	last_name VARCHAR(100) NOT NULL,
	seq_id INT NOT NULL,
	CONSTRAINT uq_ln_locale_seq UNIQUE (locale, seq_id)
);


CREATE TABLE faker.lookup_streets (
    id SERIAL PRIMARY KEY,
	locale CHAR(3) NOT NULL,
	street_name VARCHAR(150) NOT NULL,
	seq_id INT NOT NULL,
	CONSTRAINT uq_st_locale_seq UNIQUE (locale, seq_id)
);


CREATE TABLE faker.lookup_cities (
    id SERIAL PRIMARY KEY,
	locale CHAR(3) NOT NULL,
	city_name VARCHAR(100) NOT NULL,
	state_or_reqion VARCHAR(100) NOT NULL,
	postal_code_pattern VARCHAR(20) NOT NULL,
	seq_id INT NOT NULL,
	CONSTRAINT uq_ct_locale_seq UNIQUE (locale, seq_id)
);


CREATE INDEX idx_fn_lookup ON faker.lookup_first_names (locale, gender, seq_id);
CREATE INDEX idx_ln_lookup ON faker.lookup_last_names (locale, seq_id);
CREATE INDEX idx_st_lookup ON faker.lookup_streets (locale, seq_id);
CREATE INDEX idx_ct_lookup ON faker.lookup_cities (locale, seq_id);