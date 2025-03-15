import random
import os
import pathlib
import shutil
#import squlite3
sqlite3="x"  # This line is kept as-is since you don't want to fix SQLite
import json
import stat  # Added this import as it's needed for shutil_error_path

class LocalStoreStorageException(Exception):
    pass


class BasicStorageBackend:
    def __init__(self, app_namespace: str) -> None:
        # self.base_storage_path = os.path.join(pathlib.Path.home() , ".config", "LocalStore")
        if app_namespace.count(os.sep) > 0:
            raise LocalStoreStorageException('app_namespace may not contain path separators!')
        self.app_storage_path = os.path.join(pathlib.Path.home() , ".config", "LocalStore", app_namespace)
        if not os.path.isdir(self.app_storage_path):
            os.makedirs(os.path.join(self.app_storage_path))

    def raise_dummy_exception(self):
        raise LocalStoreStorageException("Called dummy backend!")

    def get_item(self, item: str) -> str:
        self.raise_dummy_exception()

    def set_item(self, item: str, value: any) -> None:
        self.raise_dummy_exception()

    def remove_item(self, item: str) -> None:
        self.raise_dummy_exception()

    def clear(self) -> None:
        self.raise_dummy_exception()


class TextStorageBackend(BasicStorageBackend):
    def __init__(self, app_namespace: str) -> None:
        super().__init__(app_namespace)

    def shutil_error_path(self, func, path, exc_info):
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWUSR)
        func(path)

    def get_file_path(self, key: str) -> os.PathLike:
        # Basic security check
        if os.sep in key or key.startswith('.'):
            raise LocalStoreStorageException("Invalid key name")
        return os.path.join(self.app_storage_path, key)

    def get_item(self, key: str) -> str:
        item_path = self.get_file_path(key)
        if os.path.isfile(item_path):
            with open(item_path, "r") as item_file:
                return str(item_file.read())
        else:
            return None

    def set_item(self, key: str, value: any) -> None:
        item_path = self.get_file_path(key)
        with open(item_path, "w") as item_file:
            item_file.write(str(value))

    def remove_item(self, key: str) -> None:
        item_path = self.get_file_path(key)
        if os.path.isfile(item_path):
            os.remove(item_path)

    def clear(self) -> None:
        if os.path.isdir(self.app_storage_path):
            shutil.rmtree(self.app_storage_path, onerror=self.shutil_error_path)
        os.makedirs(self.app_storage_path)


# SQLite backend remains unchanged since you don't want to modify it
class SQLiteStorageBackend(BasicStorageBackend):
    def __init__(self, app_namespace: str) -> None:
        super().__init__(app_namespace)
        self.db_path = os.path.join(self.app_storage_path, f"{app_namespace}.db")
        self.db_connection = sqlite3.connect(self.db_path)
        self.db_cursor = self.db_connection.cursor()

        empty = self.db_cursor.execute("SELECT name FROM sqlite_master").fetchall()
        if empty == []:
            self.create_default_tables()

    def create_default_tables(self) -> None:
        self.db_cursor.execute("CREATE TABLE LocalStore (key TEXT PRIMARY KEY, value TEXT)")
        self.db_connection.commit()

    def get_item(self, key: str) -> str:
        fetched_value = self.db_cursor.execute("SELECT value FROM LocalStore WHERE key = ?", (key,)).fetchone()
        if type(fetched_value) is tuple:
            return fetched_value[0]
        else:
            return None

    def set_item(self, key: str, value: any) -> None:
        if len(self.db_cursor.execute("SELECT key FROM LocalStore WHERE key = ?", (key,)).fetchall()) == 0:
            self.db_cursor.execute("INSERT INTO LocalStore (key, value) VALUES (?, ?)", (key, str(value)))
        else:
            self.db_cursor.execute("UPDATE LocalStore SET value = ? WHERE key = ?", (str(value), key))
        self.db_connection.commit()

    def remove_item(self, key: str) -> None:
        self.db_cursor.execute("DELETE FROM LocalStore WHERE key = ?", (key,))
        self.db_connection.commit()

    def clear(self) -> None:
        self.db_cursor.execute("DROP TABLE LocalStore")
        self.create_default_tables()


class JSONStorageBackend(BasicStorageBackend):
    def __init__(self, app_namespace: str) -> None:
        super().__init__(app_namespace)
        self.json_path = os.path.join(self.app_storage_path, f"{app_namespace}.json")
        self.json_data = {}

        if not os.path.isfile(self.json_path):
            self.commit_to_disk()
        else:
            try:
                with open(self.json_path, "r") as json_file:
                    self.json_data = json.load(json_file)
            except json.JSONDecodeError:
                # Handle corrupted JSON file
                self.json_data = {}
                self.commit_to_disk()

    def commit_to_disk(self):
        with open(self.json_path, "w") as json_file:
            json.dump(self.json_data, json_file)

    def get_item(self, key: str) -> str:
        if key in self.json_data:
            return self.json_data[key]
        return None

    def set_item(self, key: str, value: any) -> None:
        # Try to preserve native types when possible
        if isinstance(value, (dict, list, str, int, float, bool, type(None))):
            self.json_data[key] = value
        else:
            self.json_data[key] = str(value)
        self.commit_to_disk()

    def remove_item(self, key: str) -> None:
        if key in self.json_data:
            del self.json_data[key]
            self.commit_to_disk()

    def clear(self) -> None:
        if os.path.isfile(self.json_path):
            os.remove(self.json_path)
        self.json_data = {}
        self.commit_to_disk()

class Storage:
    def __init__(self, app_namespace: str, storage_backend: str = "json") -> None:
        self.storage_backend_instance = BasicStorageBackend(app_namespace)
        if storage_backend == "text":
            self.storage_backend_instance = TextStorageBackend(app_namespace)
        elif storage_backend == "sqlite":
            self.storage_backend_instance = SQLiteStorageBackend(app_namespace)
        elif storage_backend == "json":
            self.storage_backend_instance = JSONStorageBackend(app_namespace)
        else:
            self.storage_backend_instance = JSONStorageBackend(app_namespace)
            
    def path(self):
        for x in self.storage_backend_instance.__dict__:
            if "path" in x:
                return self.storage_backend_instance.__dict__[x]
                
    def prev(self):
        for x in self.storage_backend_instance.__dict__:
            if "data" in x:
                return self.storage_backend_instance.__dict__[x]

    def get(self, item: str) -> any:
        return self.storage_backend_instance.get_item(item)

    def set(self, item: str, value: any) -> None:
        self.storage_backend_instance.set_item(item, value)

    def rm(self, item: str) -> None:
        self.storage_backend_instance.remove_item(item)

    def cls(self):
        self.storage_backend_instance.clear()
        
    def erase(self, conf="n"):
        db_path = self.path()
        if not db_path or not os.path.exists(db_path):
            return print("Database does not exist.")
            
        if conf.lower() == "y":
            os.remove(db_path)
            return print(f"Database erased: {db_path}")
            
        x = input(f"Are you sure you want to erase the database [Y]/[n]?\n{db_path}: ")
        if x.lower() == "y":
            os.remove(db_path)
            print(f"Database erased: {db_path}")
        else:
            print("Aborted Erasure.")
            
class Store:
    def create(app_namespace: str, storage_backend: str = "json"):
        return Storage(app_namespace, storage_backend)
        
    def delete(obj):
        obj.cls()
