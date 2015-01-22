CREATE TABLE "dl_persons_new" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name"	TEXT NOT NULL,
	"group_id"	INTEGER NOT NULL,
	"disabled"	INTEGER DEFAULT '0'
);

INSERT INTO "dl_persons_new" (SELECT id, name, "0", disabled FROM "dl_persons");

DROP TABLE "dl_persons";
ALTER TABLE "dl_persons_new" RENAME TO "dl_persons";

CREATE TABLE "dl_groups" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name"	TEXT NOT NULL
);

INSERT INTO "dl_groups" VALUES (0, "unknown"), (1, "Munich Maker Lab e.V."), (2, "Hammer und Schild e.V.");
