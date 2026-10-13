CREATE TABLE security_config_state (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision INTEGER NOT NULL DEFAULT 0
);
INSERT INTO security_config_state(singleton,revision) VALUES(1,0);
