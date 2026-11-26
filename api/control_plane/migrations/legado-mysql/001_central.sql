-- PROPOSTA: revisar antes de executar, somente no banco CENTRAL vazio.

CREATE TABLE platform_audit (
	id INTEGER NOT NULL AUTO_INCREMENT,
	at DATETIME NOT NULL,
	actor VARCHAR(40) NOT NULL,
	action VARCHAR(50) NOT NULL,
	reference VARCHAR(80) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE platform_owner (
	id INTEGER NOT NULL,
	email VARCHAR(120) NOT NULL,
	password_hash VARCHAR(256) NOT NULL,
	auth_version INTEGER NOT NULL,
	failures INTEGER NOT NULL,
	locked_until DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT ck_platform_single_owner CHECK (id = 1),
	UNIQUE (email)
);

CREATE TABLE platform_schools (
	id INTEGER NOT NULL AUTO_INCREMENT,
	slug VARCHAR(31) NOT NULL,
	name VARCHAR(120) NOT NULL,
	domain VARCHAR(253) NOT NULL,
	state VARCHAR(20) NOT NULL,
	monthly_cents BIGINT NOT NULL,
	version INTEGER NOT NULL,
	token_hash VARCHAR(64),
	captured_at DATETIME(6),
	synced_at DATETIME(6),
	PRIMARY KEY (id),
	CONSTRAINT ck_platform_monthly CHECK (monthly_cents >= 0),
	CONSTRAINT ck_platform_school_state CHECK (state IN ('pendente','ativa','suspensa')),
	UNIQUE (slug),
	UNIQUE (domain)
);

CREATE TABLE platform_movements (
	id INTEGER NOT NULL AUTO_INCREMENT,
	school_id INTEGER NOT NULL,
	request_key VARCHAR(36) NOT NULL,
	kind VARCHAR(12) NOT NULL,
	cents BIGINT NOT NULL,
	day DATE NOT NULL,
	description VARCHAR(200) NOT NULL,
	cancelled_at DATETIME,
	cancellation_reason VARCHAR(200),
	PRIMARY KEY (id),
	CONSTRAINT ck_platform_movement_positive CHECK (cents > 0),
	CONSTRAINT ck_platform_movement_kind CHECK (kind IN ('receita','despesa')),
	FOREIGN KEY(school_id) REFERENCES platform_schools (id),
	UNIQUE (request_key)
);

CREATE TABLE platform_people (
	id INTEGER NOT NULL AUTO_INCREMENT,
	school_id INTEGER NOT NULL,
	local_id INTEGER NOT NULL,
	name VARCHAR(120) NOT NULL,
	email VARCHAR(120) NOT NULL,
	`role` VARCHAR(20) NOT NULL,
	state VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_platform_school_person UNIQUE (school_id, local_id),
	FOREIGN KEY(school_id) REFERENCES platform_schools (id)
);
