#!/usr/bin/env python3
import sqlite3
import logging
import argparse
import sys
import hashlib

from prettytable import from_db_cursor

# config
DATABASE = 'doorlock.db'


def create_hash(text):
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()


# parse arguments
parser = argparse.ArgumentParser()
parser_subs = parser.add_subparsers(help='entity help', dest='entity')

parser_person = parser_subs.add_parser('person', help='a help')
parser_person_subs = parser_person.add_subparsers(help='sub-command help', dest='action')
parser_person_create = parser_person_subs.add_parser('create', help='create a new person')
parser_person_create.add_argument("name")
parser_person_create.add_argument("group_id")
parser_person_list = parser_person_subs.add_parser('list', help='list persons')
parser_person_enable = parser_person_subs.add_parser('enable', help='enable a person to unlock the door')
parser_person_enable.add_argument("name")
parser_person_disable = parser_person_subs.add_parser('disable', help='disable a person to unlock the door')
parser_person_disable.add_argument("name")
parser_person_remove = parser_person_subs.add_parser('remove', help='remove a person')
parser_person_remove.add_argument("name")


parser_person_rename = parser_person_subs.add_parser('rename', help='rename a person')
parser_person_rename.add_argument("old_name")
parser_person_rename.add_argument("new_name")
parser_person_show = parser_person_subs.add_parser('show', help='show details about a person')
parser_person_show.add_argument("name")

parser_token = parser_subs.add_parser('token', help='a help')
parser_token_subs = parser_token.add_subparsers(help='sub-command help', dest='action')
parser_token_add = parser_token_subs.add_parser('add', help='add a new token')
parser_token_add.add_argument("person")
parser_token_add.add_argument("token")
parser_token_add.add_argument("pin")
parser_token_reset = parser_token_subs.add_parser('reset', help='reset pin')
parser_token_reset.add_argument("person")
parser_token_reset.add_argument("pin")
parser_token_remove_desc = 'Removes a token from the database. You can find the list of a users tokens by running "person show <name>"'
parser_token_remove = parser_token_subs.add_parser('remove', help='remove a token', description=parser_token_remove_desc)
parser_token_remove.add_argument("token")

args = parser.parse_args()

# get logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("manage_db")
logger.info("Starting doorlock backend")

# instantiate db connection
conn = sqlite3.connect(DATABASE)
c = conn.cursor()
logger.debug("Database opened")

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='dl_persons' OR name='dl_tokens');")

if c.fetchone() is None:
    logger.warning("Tables do not exist. Creating them.")
    sqlscript = open('doorlock.db.sql', 'r')
    c.executescript(sqlscript.read())

# Person actions
if args.entity == "person":
    # Create new person
    if args.action == "create":
        t = (args.name,)
        c.execute("SELECT * FROM dl_persons WHERE name=?;", t)
        if c.fetchone() is not None:
            logger.error("Person '%s' already exists.", args.name)
            sys.exit(1)

        t = (args.name, args.group_id,)
        c.execute("INSERT INTO dl_persons(name, group_id, disabled) VALUES (?, ?, '0');", t)
        if c.rowcount == 1:
            logger.info("Person '%s' successfully created.", args.name)
        else:
            logger.error("Error while creating person'%s'.", args.name)

    elif args.action == "remove":
        t = (args.name,)
        c.execute("SELECT id FROM dl_persons WHERE name=?;", t)
        row = c.fetchone()
        if row is None:
            logger.error("Person '%s' does not exist.", args.name)
            sys.exit(1)

        logger.info("Removing person '%s'.", args.name)
        t = (row[0],)
        c.execute("DELETE FROM dl_persons WHERE id=?;", t)
        if c.rowcount == 1:
            logger.info("Person '%s' successfully removed.", args.name)
        else:
            logger.error("Error while removing person.")

    elif args.action == "list":
        print("Active Members:")
        c.execute("SELECT p.name 'Name', p.disabled 'Disabled?', COUNT(t.id) 'No of tokens' FROM (dl_persons p LEFT JOIN dl_tokens t ON t.person_id = p.id) WHERE p.disabled = 0 GROUP BY p.id ORDER BY p.name;")
        pt = from_db_cursor(c)
        pt.align = "l"
        print(pt)

        print("\n Inactive Members:")
        c.execute("SELECT p.name 'Name', p.disabled 'Disabled?', COUNT(t.id) 'No of tokens' FROM (dl_persons p LEFT JOIN dl_tokens t ON t.person_id = p.id) WHERE p.disabled != 0 GROUP BY p.id ORDER BY p.name;")
        pt = from_db_cursor(c)
        print(pt)

    elif args.action == "disable" or args.action == "enable":
        t = (args.name,)
        c.execute("SELECT * FROM dl_persons WHERE name=?;", t)
        if c.fetchone() is None:
            logger.error("Person '%s' does not exist.", args.name)
            sys.exit(1)

        if args.action == "disable":
            c.execute("UPDATE dl_persons SET disabled = 1 WHERE name=?;", t)
        else:
            c.execute("UPDATE dl_persons SET disabled = 0 WHERE name=?;", t)
        if c.rowcount == 1:
            logger.info("Person '%s' successfully %sd.", args.name, args.action)
        else:
            logger.error("Error while disabling person'%s'.", args.name)

    elif args.action == "rename":
        t = (args.old_name,)
        c.execute("SELECT * FROM dl_persons WHERE name=?;", t)
        if c.fetchone() is None:
            logger.error("Person '%s' does not exist.", args.old_name)
            sys.exit(1)

        t = (args.new_name,)
        c.execute("SELECT * FROM dl_persons WHERE name=?;", t)
        if c.fetchone() is not None:
            logger.error("Person '%s' already exists.", args.new_name)
            sys.exit(1)

        t = (args.new_name, args.old_name,)
        c.execute("UPDATE dl_persons SET name = ? WHERE name=?;", t)
        if c.rowcount == 1:
            logger.info("Person '%s' successfully renamed to '%s'.", args.old_name, args.new_name)
        else:
            logger.error("Error while renaming person'%s'.", args.old_name)

    elif args.action == "show":
        t = (args.name,)
        c.execute("SELECT dl_persons.id, dl_persons.name, dl_persons.disabled FROM dl_persons WHERE dl_persons.name=?;", t)
        row = c.fetchone()
        if row is None:
            logger.error("Person '%s' does not exist.", args.name)
            sys.exit(1)

        name = row[1]
        if row[2] == 0:
            status = "ENABLED"
        else:
            status = "DISABLED"
        print(name)
        print("==============")
        print("status: %s\n" % status)

        print("Tokens:")
        t = (row[0],)
        c.execute("SELECT token FROM dl_tokens WHERE person_id=?;", t)
        tokenCount = 0
        for token in c:
            print("    %s" % token[0])
            tokenCount = tokenCount + 1
        if tokenCount == 0:
            print("    No Tokens")

# Token actions
elif args.entity == "token":
    if args.action == "add":
        t = (args.person,)
        c.execute("SELECT id FROM dl_persons WHERE name=?;", t)
        row = c.fetchone()
        if row is None:
            logger.error("Person '%s' does not exist.", args.person)
            sys.exit(1)

        t = (args.token, create_hash(args.token + ":" + args.pin),)
        c.execute("SELECT * FROM dl_tokens WHERE token=? AND pin =?;", t)
        if c.fetchone() is not None:
            logger.error("Token already exists.")
            sys.exit(1)

        t = (row[0], args.token, create_hash(args.token + ":" + args.pin),)
        c.execute("INSERT INTO dl_tokens(person_id, token, pin) VALUES (?,?,?);", t)
        if c.rowcount == 1:
            logger.info("Token for '%s' successfully created.", args.person)
        else:
            logger.error("Error while adding token.")

    elif args.action == "reset":
        t = (args.person,)
        c.execute("SELECT id FROM dl_persons WHERE name=?;", t)
        row = c.fetchone()
        if row is None:
            logger.error("Person '%s' does not exist.", args.person)
            sys.exit(1)

        t = (row[0],)
        c.execute("SELECT person_id, token FROM dl_tokens WHERE person_id=?;", t)
        row = c.fetchone()
        if row is not None:
            if c.fetchone() is not None:
                logger.error("Not implemented.")
                sys.exit(1)

            logger.info("One token for '%s'found. Changing PIN...", args.person)
            t = (create_hash(row[1] + ":" + args.pin), row[0], row[1],)
            c.execute("UPDATE dl_tokens SET pin=? WHERE person_id=? AND token=?;", t)
            if c.rowcount == 1:
                logger.info("PIN for '%s' successfully updated.", args.person)
            else:
                logger.error("Error while updating pin.")
        else:
            logger.error("No token found.")

    elif args.action == "remove":
        t = (args.token,)
        c.execute("SELECT id FROM dl_tokens WHERE token=?;", t)
        row = c.fetchone()
        if row is None:
            logger.error("Token '%s' does not exist.", args.token)
            sys.exit(1)

        logger.info("Removing token '%s'.", args.token)
        t = (row[0],)
        c.execute("DELETE FROM dl_tokens WHERE id=?;", t)
        if c.rowcount == 1:
            logger.info("Token '%s' successfully removed.", args.token)
        else:
            logger.error("Error while removing token.")

conn.commit()
conn.close()
