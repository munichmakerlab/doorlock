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
parser_person_list = parser_person_subs.add_parser('list', help='list persons')
parser_person_enable = parser_person_subs.add_parser('enable', help='enable a person to unlock the door')
parser_person_enable.add_argument("name")
parser_person_disable = parser_person_subs.add_parser('disable', help='disable a person to unlock the door')
parser_person_disable.add_argument("name")
parser_person_rename = parser_person_subs.add_parser('rename', help='rename a person')
parser_person_rename.add_argument("old_name")
parser_person_rename.add_argument("new_name")

parser_token = parser_subs.add_parser('token', help='a help')
parser_token_subs = parser_token.add_subparsers(help='sub-command help', dest='action')
parser_token_add = parser_token_subs.add_parser('add', help='add a new token')
parser_token_add.add_argument("person")
parser_token_add.add_argument("token")
parser_token_add.add_argument("pin")


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
		
		# Add new person
		c.execute("INSERT INTO dl_persons(name, disabled) VALUES (?, '0');",t)
		if c.rowcount == 1:
			logger.info("Person '%s' successfully created.", args.name)
		else:
			logger.error("Error while creating person'%s'.",args.name)
	
	# List all persons
	elif args.action == "list":
		c.execute("SELECT p.name Name, p.disabled 'Disabled?', COUNT(t.id) 'No of tokens' from dl_persons p LEFT JOIN dl_tokens t ON t.person_id = p.id GROUP BY p.id;")
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
		t = (args.token,create_hash(args.pin),)
		c.execute("SELECT * FROM dl_tokens WHERE token=? AND pin =?;",t)
		if c.fetchone() != None:
			logger.error("Token already exists.")
			sys.exit(1)
		
		# Create token
		t = (row[0],args.token,create_hash(args.pin),)
		c.execute("INSERT INTO dl_tokens(person_id, token, pin) VALUES (?,?,?);",t)
		if c.rowcount == 1:
			logger.info("Token for '%s' successfully created.", args.person)
		else:
			logger.error("Error while adding token.")


conn.commit()
conn.close()
