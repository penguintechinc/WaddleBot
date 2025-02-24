# -*- coding: utf-8 -*-
import json
from urllib.parse import unquote
import logging


# try something like
def index(): return dict(message="hello from marketplace.py")

# Function to decode names with space in
from urllib.parse import unquote

def decode_name(name):
    if not name:
        return None
    return unquote(name)
    if not name:
        return None
    name = name.replace("%20", " ")
    name = name.replace("_", " ")

    return name

# Create a new marketplace module from a given payload. Throws an error if no payload is given, or the marketplace module already exists.
def create():
    payload = request.body.read()
    if not payload:
        return dict(msg="No payload given.")
    payload = json.loads(payload)
    if 'name' not in payload or 'description' not in payload or 'gateway_url' not in payload or 'module_type_id' not in payload or 'metadata' not in payload:
        return dict(msg="Payload missing required fields.")
    if db(db.marketplace_modules.name == payload['name']).count() > 0:
        return dict(msg="Marketplace Module already exists.")
    db.marketplace_modules.insert(**payload)
    return dict(msg="Marketplace Module created.")

# Get a marketplace module by name. Throws an error if no name is given, or the marketplace module does not exist.
def get():
    name = decode_name(request.args(0))
    if not name:
        return dict(msg="No name given.")
    marketplace_module = db(db.marketplace_modules.name == name).select().first()
    if not marketplace_module:
        return dict(msg="Marketplace Module does not exist.")

    # Also return the marketplace module type name part of the response
    module_type = db(db.module_types.id == marketplace_module.module_type_id).select().first()
    marketplace_module = marketplace_module.as_dict()
    marketplace_module['module_type_name'] = module_type.name    

    return marketplace_module

# Get all marketplace modules.
def get_all():
    marketplace_modules = db(db.marketplace_modules).select()
    # Add the module type name to each marketplace module
    for marketplace_module in marketplace_modules:
        module_type = db(db.module_types.id == marketplace_module.module_type_id).select().first()
        marketplace_module.module_type_name = module_type.name
    return dict(data=marketplace_modules)

# Get all the marketplace modules, as only the name and the id. Only modules that fall under the Community module type are returned.
def get_all_community_modules():
    community_module_type = db(db.module_types.name == "Community").select().first()
    marketplace_modules = db(db.marketplace_modules.module_type_id == community_module_type.id).select(db.marketplace_modules.id, db.marketplace_modules.name)
    return dict(data=marketplace_modules)

# Get a marketplace module by URL. Throws an error if no URL is given, or the marketplace module does not exist. Also returns the module type name.
def get_by_url():
    url = request.vars.url

    if not url:
        return dict(msg="No URL given.")

    url = unquote(url)

    marketplace_module = db(db.marketplace_modules.gateway_url == url).select().first()
    if not marketplace_module:
        return dict(msg="Marketplace Module does not exist.")
    
    # Also return the marketplace module type name part of the response
    module_type = db(db.module_types.id == marketplace_module.module_type_id).select().first()
    marketplace_module = marketplace_module.as_dict()
    marketplace_module['module_type_name'] = module_type.name

    return marketplace_module

# Remove a marketplace module by name. Throws an error if no name is given, or the marketplace module does not exist.
def remove():
    name = decode_name(request.args(0))
    if not name:
        return dict(msg="No name given.")
    marketplace_module = db(db.marketplace_modules.name == name).select().first()
    if not marketplace_module:
        return dict(msg="Marketplace Module does not exist.")
    db(db.marketplace_modules.name == name).delete()
    return dict(msg="Marketplace Module removed.")

# Update a marketplace module by name. Throws an error if no name is given, or the marketplace module does not exist.
def update():
    name = decode_name(request.args(0))
    if not name:
        return dict(msg="No name given.")
    marketplace_module = db(db.marketplace_modules.name == name).select().first()
    if not marketplace_module:
        return dict(msg="Marketplace Module does not exist.")
    payload = request.body.read()
    if not payload:
        return dict(msg="No payload given.")
    payload = json.loads(payload)
    marketplace_module.update_record(**payload)
    return dict(msg="Marketplace Module updated.")


