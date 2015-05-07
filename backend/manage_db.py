#!/usr/bin/env python
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
	h.update(text)
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
parser_token_remove = parser_token_subs.add_parser('remove', help='remove a token')
parser_token_remove.add_argument("token")

parser_group = parser_subs.add_parser('group', help='a help')
parser_group_subs = parser_group.add_subparsers(help='sub-command help', dest='action')
parser_group_list = parser_group_subs.add_parser('list', help='list groups')

args = parser.parse_args()

# get logger
logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)
logger = logging.getLogger("manage_db")
logger.info("Starting doorlock backend")

# instantiate db connection
conn = sqlite3.connect(DATABASE)
c = conn.cursor()
logger.debug("Database opened")

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='dl_persons' OR name='dl_tokens');")

if c.fetchone() == None:
	logger.warning("Tables do not exist. Creating them.")
	sqlscript = open('doorlock.db.sql','r')
	c.executescript(sqlscript.read())

# Person actions
if args.entity == "person":
	# Create new person
	if args.action == "create":
		# Check whether person already exists
		t = (args.name,)
		c.execute("SELECT * FROM dl_persons WHERE name=?;",t)
		if c.fetchone() != None:
			logger.error("Person '%s' already exists.",args.name)
			sys.exit(1)
		
		# Check whether person already exists
		t = (args.group_id,)
		c.execute("SELECT * FROM dl_groups WHERE id=?;",t)
		if c.fetchone() == None:
			logger.error("Group '%s' does not exist.",args.group_id)
			sys.exit(1)
		
		# Add new person
		t = (args.name, args.group_id,)
		c.execute("INSERT INTO dl_persons(name, group_id, disabled) VALUES (?, ?, '0');",t)
		if c.rowcount == 1:
			logger.info("Person '%s' successfully created.", args.name)
		else:
			logger.error("Error while creating person'%s'.",args.name)
	
	# List all persons
	elif args.action == "list":
		c.execute("SELECT g.name 'Group', p.name 'Name', p.disabled 'Disabled?', COUNT(t.id) 'No of tokens' FROM (dl_persons p LEFT JOIN dl_tokens t ON t.person_id = p.id) INNER JOIN dl_groups g ON p.group_id = g.id GROUP BY p.id, g.id ORDER BY g.name, p.name;")
		pt = from_db_cursor(c)
		print pt
	
	# Enable / Disable persons
	elif args.action == "disable" or args.action == "enable":
		# Check whether person exists
		t = (args.name,)
		c.execute("SELECT * FROM dl_persons WHERE name=?;",t)
		if c.fetchone() == None:
			logger.error("Person '%s' does not exist.",args.name)
			sys.exit(1)
		
		if args.action == "disable":
			c.execute("UPDATE dl_persons SET disabled = 1 WHERE name=?;",t)
		else:
			c.execute("UPDATE dl_persons SET disabled = 0 WHERE name=?;",t)
		if c.rowcount == 1:
			logger.info("Person '%s' successfully %sd.", args.name, args.action)
		else:
			logger.error("Error while disabling person'%s'.",args.name)

	# Rename a person
	elif args.action == "rename":
		# Check whether person exists
		t = (args.old_name,)
		c.execute("SELECT * FROM dl_persons WHERE name=?;",t)
		if c.fetchone() == None:
			logger.error("Person '%s' does not exist.",args.old_name)
			sys.exit(1)
		
		t = (args.new_name,)
		c.execute("SELECT * FROM dl_persons WHERE name=?;",t)
		if c.fetchone() != None:
			logger.error("Person '%s' already exists.",args.new_name)
			sys.exit(1)
		
		t = (args.new_name,args.old_name,)
		c.execute("UPDATE dl_persons SET name = ? WHERE name=?;",t)
		if c.rowcount == 1:
			logger.info("Person '%s' successfully renamed to '%s'.", args.old_name, args.new_name)
		else:
			logger.error("Error while renaming person'%s'.",args.old_name)

	elif args.action == "show":
		# Check whether person exists
		t = (args.name,)
		c.execute("SELECT dl_persons.id, dl_persons.name, dl_groups.name, dl_persons.disabled FROM dl_persons, dl_groups WHERE dl_persons.name=? AND dl_groups.id=dl_persons.group_id;",t)
		row = c.fetchone()
		if row == None:
			logger.error("Person '%s' does not exist.",args.name)
			sys.exit(1)

		# Print person details
		name = row[1]
		group = row[2]
		if row[3] == 0:
			status = "ENABLED"
		else:
			status = "DISABLED"
		print name
		print "=============="
		print "group:  %s" % group
		print "status: %s\n" % status

		# Print token list
		print "Tokens:"
		t = (row[0],)
		c.execute("SELECT token FROM dl_tokens WHERE person_id=?;",t)
		tokenCount = 0
		for token in c:
			print "    %s" % token[0]
			tokenCount = tokenCount + 1
		if tokenCount == 0:
			print "    No Tokens"

# Token actions
elif args.entity == "token":
	# Add new token
	if args.action == "add":
		# Check whether person exists
		t = (args.person,)
		c.execute("SELECT id FROM dl_persons WHERE name=?;",t)
		row = c.fetchone()
		if row == None:
			logger.error("Person '%s' does not exist.", args.person)
			sys.exit(1)
		
		# Check whether token is already used
		t = (args.token,create_hash(args.token + ":" + args.pin),)
		c.execute("SELECT * FROM dl_tokens WHERE token=? AND pin =?;",t)
		if c.fetchone() != None:
			logger.error("Token already exists.")
			sys.exit(1)
		
		# Create token
		t = (row[0],args.token,create_hash(args.token + ":" + args.pin),)
		c.execute("INSERT INTO dl_tokens(person_id, token, pin) VALUES (?,?,?);",t)
		if c.rowcount == 1:
			logger.info("Token for '%s' successfully created.", args.person)
		else:
			logger.error("Error while adding token.")
	elif args.action == "reset":
		# Check whether person exists
                t = (args.person,)
                c.execute("SELECT id FROM dl_persons WHERE name=?;",t)
                row = c.fetchone()
                if row == None:
                        logger.error("Person '%s' does not exist.", args.person)
                        sys.exit(1)
		
		t = (row[0],)
		c.execute("SELECT person_id, token FROM dl_tokens WHERE person_id=?;", t)
		row = c.fetchone()
		if row != None:
			if c.fetchone() != None:
				logger.error("Not implemented.")
				sys.exit(1)

			logger.info("One token for '%s'found. Changing PIN...", args.person)
			t = (create_hash(row[1] + ":" + args.pin),row[0],row[1],)
			c.execute("UPDATE dl_tokens SET pin=? WHERE person_id=? AND token=?;",t)
			if c.rowcount == 1:
	                        logger.info("PIN for '%s' successfully updated.", args.person)
                	else:
                        	logger.error("Error while updating pin.")
		else:
			logger.error("No token found.")
        elif args.action == "remove":
		# Check whether token exists
		t = (args.token,)
		c.execute("SELECT id FROM dl_tokens WHERE token=?;",t)
		row = c.fetchone()
		if row == None:
			logger.error("Token '%s' does not exist.", args.token)
			sys.exit(1)

		logger.info("Removing token '%s'.", args.token)
		t = (row[0],)
		c.execute("DELETE FROM dl_tokens WHERE id=?;",t)

# Group actions
elif args.entity == "group":
	if args.action == "list":
		c.execute("SELECT g.name 'Group', COUNT(p.id) 'No of people', COUNT(t.id) 'No of tokens', g.id 'Group ID' FROM (dl_persons p LEFT JOIN dl_tokens t ON t.person_id = p.id) INNER JOIN dl_groups g ON p.group_id = g.id GROUP BY g.id ORDER BY g.name;")
		pt = from_db_cursor(c)
		print pt

conn.commit()
conn.close()
