# WaddleBot DBM Core Modules

## Introduction
The waddlebot DBM core modules are python script modules that are built on the web2py framework. These core modules are built within the waddlebot environment and runs on a combined web2py container. These modules are queried by the listener, via commands stored in the waddlebot-redis module, and stores data in a locally shared sqllite database (database type still under discussion). 

Web2PY documentation:
https://www.web2py.com/book

## Module Setup
To setup and run this module for testing purposes in a local installation of web2py, do the following:

### Local web2py setup

1. Ensure that you have python installed on your PC with a minimum version of 3.7

2. Navigate to https://www.web2py.com/examples/default/download

3. Download the "Source Code" version of web2py. This version allows for the use of external python libraries.

4. Extract the zip file to anywhere on your pc.

5. Create a new file in the root directory of the newly extracted folder, called "run.bat".

6. Edit run.bat with your prefered code editor (such as vscode) and input the following command:

```python3 web2py.py -a root -i 127.0.0.1 -p 8000```

7. The above command will execute web2py when double clicked, with the following parameters:
    - "-a": Sets the administrator console password for debugging.
    - "-i": Sets the IP address of where web2py will be hosted.
    - "-p": Sets the port on which web2py will be listening on.

8. To run web2py with the above command in mind, execute the newly created "run.bat" file, or run that command in the root directory of web2py (where the file web2py.py is located).

9. To check if web2py is running, navigate to http://127.0.0.1:8000/ in your web browser (or your respective given IP address and port number combination). If a web2py UI is shown, it means web2py is successfully installed and running.

### Project setup

1. After web2py has been succesfully installed, ensure that git is setup correctly with your credentials on your pc. A small tutorial: https://phoenixnap.com/kb/how-to-install-git-windows

2. Run the following command to pull the project from github:

```git pull https://github.com/PenguinCloud/WaddleDBM.git```

3. Navigate to the "applications" folder of web2py, found in its root directory.

4. Copy the top level folder of the web2py project (in this case its "WaddleDBM") into the "applications" folder.

5. In the root folder of web2py, run "run.bat" (or the console command mentioned in [Local web2py setup](#local-web2py-setup)), or refresh the browser if its already running.

6. The project should be running now. To view that the application is setup correctly, navigate to: http://127.0.0.1:8000/WaddleDBM/default/index

## DBM Module structure

Each WaddleDBM core module found within the DBM module, consists of the following sections:

1. One or more DB tables that is defined in the db.py file. This file is located in `/WaddleDBM/models/db.py` (link: https://github.com/PenguinCloud/WaddleDBM/blob/main/models/db.py)

2. A controller .py file that is responsible for all the core DBM module endpoints, located in `/WaddleDBM/controllers` (link: https://github.com/PenguinCloud/WaddleDBM/tree/main/controllers)

3. An entry in the modules table of the DB (might need to rename this table, because it does contain a module type pointing towards whether its a core module, or a marketplace module that needs to be installed).

4. An entry in the waddlebotCore's REDIS table.

5. Any necessary views for if UI's are required for input, outside of matterbridge.

### Table declaration

All core DBM modules that need to store data within the DBM, need to declare their associated tables within the db.py file first, located in `/WaddleDBM/models/db.py` (https://github.com/PenguinCloud/WaddleDBM/blob/main/models/db.py) of the WaddleDBM project.

WaddleDBM uses the python library PyDAL (python database abstraction layer), built within web2py, to handle any database communication. PyDAL uses its own built in functions for database interaction that functions crossplatform, between database engines, so no need to adapt sql functions if needed. 

Full Pydal documentation can be found at: https://pydal.readthedocs.io/en/latest/

To declare a new table, do the following:

1. Open the above mentioned db.py file in a code editor of your choice (such as vscode).

2. Table declaration starts at [line 160](https://github.com/PenguinCloud/WaddleDBM/blob/600a5c25b0af87993671044476b0be5110b33c43/models/db.py#L160)

3. Basic table declaration is handled through the following PyDAL command:

```
db.define_table('my_table_name',
            Field('my_first_field', 'field_type'),
            Field('my_second_field', 'field_type')
            etc.....)
```

A small breakdown of the command is as follows:

- "db": Instance of the current db PyDAL object. This should always remain the same variable name throughout.
- "define_table": Runs a function within the "db" PyDAL object called "define_table", that creates a new table under the "db" instance.
- "'my_table_name'": This is the first parameter of the function, which is the name of the table.
- "Field": Defines columns within the given table, listed as many as needed, seperated with commas (indicating each as a new column), containing the following parameters:
    - "'field_name'('my_first_field' as an example)": Defines the column name.
    - "'field_type'": Defines the datatype of the field ('string', 'integer' etc...). A full list of data types can be found at https://web2py.com/books/default/chapter/29/06/the-database-abstraction-layer#Field-types
    - Any additional field parameters can be found at https://web2py.com/books/default/chapter/29/06/the-database-abstraction-layer#Field-constructor

A quick note, the above command autogenerates the "id" column/field, so no need to create it yourself. To reference a different table, add the following field:

```
Field('my_foreign_key_field', db.table_name)
```

4. PyDAL declares tables in an order from top to bottom in the script, so remember, if you want to reference a different table, ensure that the table being referenced is defined first in the list, before defining a table that requires that table as a foreign key.

### Controller files

Now that the core module's tables have been defined, its time to start creating API endpoints to start interaction with the module and its tables. This is done via controller .py files, located in `/WaddleDBM/controllers` (link: https://github.com/PenguinCloud/WaddleDBM/tree/main/controllers).

All endpoints are contained within a singular controller.py file for the given module, that is exposed as endpoints by web2py for the listener and the rest of the web2py core modules to use. 

The structure of these controller files, are essentially the same as any python script file. The difference being that:

- the pydal "db" object, mentioned in the previous section, is freely available throughout all controllers in the web2py WaddleDBM application, without import and declaration, as well as a few other libraries, such as "requests".

- Each function is exposed as an API endpoint to interact with the module, via HTTP requests. These requests will be executed through the url http://127.0.0.1:8000/WaddleDBM/my_module/my_endpoint_name.json, where "my_module" is the name of the controller file and "my_endpoint_name.json" is the name of the endpoint function, with .json at the end, defined as a normal python function, that should return as much as possible, a dictionary:

```
def my_endpoint_name():
    return dict(msg="I did stuff!")
```

To create a module controller with simple interaction, do the following:

1. Navigate to the "controllers" folder of the the WaddleDBM application.

2. Create a new python script that contains the name of your module that you want to create. Example:

`my_module.py`

3. Open the newly created script file with a text editor of your choice.

4. Add the following code:

```
def test_function():
    testOutput = "Hello World"
    return dict( data = testOutput)
```

5. Save the file.

6. With web2py running and WaddleDBM in the applications folder, open your browser and navigate to http://127.0.0.1:8000/WaddleDBM/my_module/test_function.json. 

7. If everything worked, the browser should display a json object, containing:

```
{"data": "Hello World"}
```

With the above example, we created a simple module action endpoint that can return data, or do something else with the module, from an HTTP request. These request methods are the main method that external applications, including most importantly, the listener, can interact with WaddleBOT. 

Now for some basic database interaction with your new module's tables.

Lets assume you have a table created, called "my_table", that contains the fields/columns "name", and "email". Lets add a function that creates a new record in this table:

1. With your code editor still open from the previous example in your module, lets add the following code:

```
def create_record():
    name = request.args(0)
    email = request.args(1)

    db.my_table.insert(name=name, email=email)

    return(msg="Record successfully inserted!")
```

2. With web2py running and WaddleDBM in the applications folder, open your browser and navigate to http://127.0.0.1:8000/WaddleDBM/my_module/create_record.json/test/testemail

3. If everything worked, the browser should display a json object, containing:

```
{"msg": "Record successfully inserted!"}
```

We can see that within the json object that was returned, the record was inserted. The next step, is to retrieve the record. The follow example, retrieves all the records:

1. With your code editor still open from the previous example in your module, lets add the following code:

```
def get_all()
    records = db(db.my_table).select()
    return(data=records)
```

2. With web2py running and WaddleDBM in the applications folder, open your browser and navigate to http://127.0.0.1:8000/WaddleDBM/my_module/get_all.json 

3. If everything worked, the browser should display a json object, containing:

```
{
    "data" : [
        {
            "id": 1, 
            "name": "test",
            "email": "testemail"
        }
    ]
}
```

There are many other things that you can do with these endpoint functions, but the above examples provided the most basic functions to get started. For a full documentation of PyDAL's database interactions, go to https://web2py.com/books/default/chapter/29/06/the-database-abstraction-layer#Run-time-field-and-table-modification

### Modules Table entry

After a new module has been created in the WaddleDBM, the first step for the listener to interact with this module, is through the creation of a record in the modules table. All modules found within WaddleDBM must contain a record within this table to store metadata of each command within each module.

The modules table requires the following fields:

1. name (type: string) 
2. description (type: string) 
3. gateway_url (type: string)
4. module_type_id (type: string)  
5. metadata (type: json)

The module_type_id, in the case of the core modules, must always be 1 (pointing that the given module is a core module).

The metadata, in JSON format, contains all the necessary commands, written also as JSON objects, that is bound to the given module. 

For each command to be understood properly by Waddlebot's Matterbridge listener, each command in the metadataobject, is written as a object key in the following format:

```
{
    "!full_command_written_as_this": {
        "action": "http://127.0.0.1:8000/WaddleDBM/my_module/my_function_name.json",
        "description": "A description of the command is listef here, as well as an example. Example: !full command written as this [my_value] <my_parameter>",
        "method": "POST",
        "parameters": [
            "my_parameter"
        ],
        "payload_keys": [
            "community_name",
            "identity_name",
            "my_value"
        ],
        "req_priv_list": [
            "Owner"
        ]
    }
    "!here_is_another_command"{
        etc....
    }
}
```

Description of each key in the object:

- "!full_command_written_as_this": This is the full name of the command. When the command is typed on the front signals (Twitch, Discord channels), the "_" characters represent spaces. The full name of the command also contains the rest of the command values as an object value.
- "action": This key contains the action URL of the bound command. Essentially, when the full command name is typed, this action URL is executed in the HTTP request.
- "description": This key represents a value that is returned when the command is executed, but missing some information from being executed correctly.
- "method": This key represents the HTTP request method that the listener uses to executed the action request.
- "parameters": This key contains a list of parameters that is listed part of the URL, seperated with "/" characters. These parameter values must be URL encoded to work properly and is written between "<>" characters in a given command. Example: `!full command written as this <my_parameter>`
- "payload_keys": This key contains a list of payload values that is sent as a json request body object from the listener. They dont need to be encoded and are written between "[]" characters. Example: `!full command written as this [my_parameter]`.
- "req_priv_list": This key contains a list of required privilages that a user must have to execute this command. The privilages is are retrieved by the listener and sent as part of the request.

A quick note. The following payload keys are auto added by the listener when a command is executed and dont need to be added to the command on the signals:

- "community_name"
- "identity_name"

If a module requires these parameters for data processing or validation, these payload keys need to be added to the command metadata "payload_keys" object key.

Modules are currently added to this table, through the module onboarding platform that is part of the WaddleDBM (https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/module_onboarding.py).

### WaddleBot Core REDIS entry

Combined with the previous table entry in the DBM, each command must be added to the Waddlebot Core REDIS cache that the listener is connected to. Each command is written as a key value pair, where the key is the full command (spaces replaced with "_" characters), and the value being the name of the module.

Currently in the testing/dev branch of REDIS, commands are added when the listener starts in the core module through the following variable:

```
testCommands = {
    # Community related commands
    "!community": "Community",
    # Context related commands
    "!namespace": "Context",
    # Marketplace Related Commands
    "!marketplace": "Marketplace",
    # Gateway route related commands
    "!gateway": "Gateway Manager",
    # Routing related commands
    "!route": "Routing Manager",
    # Currency related commands
    "!currency": "Currency",
    # Admin related commands
    "!admin": "Admin Context",
    # Test script related commands
    "#test": "Test Module"
}
```

(W.I.P)

### UI Views

Another component that is also implemented on certain modules that require additional inputs where commands wont work, or where sensitive data is used, are views. Views are HTML files that contain all the necessary inputs of a given module and interacts with a controller to store any necessary information. 

To setup a view, do the following:

1. In the WaddleDBM folder, navigate to the "Views" folder.

2. Create a new .html file, called my_view.html, and open it in a code editor of your choice.

3. Add the following HTML code:

```
{{extend 'waddle_layout.html'}}
<p>
    Hello World!
</p>
{{=test_form}}
```

4. In the "my_module" controller file, add the following code to create a new function for the form:

```
def test_form():
    test_form = SQLFORM(db.my_table, fields=['name', 'email'])

    db.my_table.insert(**test_form.vars)
    
    return dict(test_form=test_form)
```

5. Assuming you have web2py running, navigate to http://127.0.0.1:8000/WaddleDBM/my_module/test_form on your webbrowser.

6. If everything worked correctly, you will see a UI that contains the fields "name" and "email"

The above form will allow you to insert data into your newly created table. For more information regarding views, visit https://www.tutorialspoint.com/web2py/web2py_views.htm

## Core DBM Modules

The base functionality of WaddleDBM contains the following modules (As of v1.1.0 test)

- Communities
- Identities
- Command Alias Module
- Calender Module
- Community Modules
- Community Roles
- Admin Context Module
- Currency Module
- Gateway Manager
- Routing Module
- Giveaway Module
- Identity Label Module
- Marketplace Module
- Module Onboarding
- Text Response Module

## DB Initialization

When the WaddleDBM module starts up, some initial values need to be created in the DB for some features of the DBM to work properly. To do this, a script class called db_initializer is used. 

This class object contains some helper functions to read data from given JSON files, and load data into given table, if they dont exists yet. The script can be found at https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/scripts/init_db.py

Currently, all the following tables receive default values on startup:

- modules
- module_types
- prize_statusses
- account_types
- gateway_server_types
- gateway_types
- gateway_accounts
- gateway_servers

During DB initialization, the "Global" community is also created and contain the following default roles, with their accompanying privileges that is used by certain module functions, if stipulated in the "modules" table, for each stored command in a module:

| Role          | Privileges                                |
| ------------- | ----------------------------------------- |
| Administrator | read, write, update, delete, admin, owner |
| Moderator     | read, write, update, delete               |
| User          | read                                      |

(This readme is still very W.I.P)

