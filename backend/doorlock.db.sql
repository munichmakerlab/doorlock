CREATE TABLE "dl_groups" (
        "id"    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name"  TEXT NOT NULL
);

CREATE TABLE "dl_persons" (
        "id"    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name"  TEXT NOT NULL,
        "group_id"      INTEGER NOT NULL,
        "disabled"      INTEGER DEFAULT '0'
);

CREATE TABLE "dl_tokens" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"person_id"	INTEGER NOT NULL,
	"token"	TEXT NOT NULL,
	"pin"	TEXT NOT NULL
);
