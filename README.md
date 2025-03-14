# Store
Barebones utility to store data without any messy code

### Installation:
```
pip install localstore
```

### Usage:
```python
#import
from store import Store
#creation
db = Store.create("databasename")
#get path to database
path = db.path()
#add values
db.set("key",[1,2,3,4])
#get values
db.get("key")
#remove values
db.rm("key")
#clear the database (requires confirmation if not specified as erase(conf="y")
db.erase()
#delete the database
Store.delete(db)
```
