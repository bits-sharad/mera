from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Union, List

# Type variable for the entity type
T = TypeVar("T")
# Type variable for the ID type, defaulting to Union[str, object]
ID = TypeVar("ID", bound=Union[str, object])


class Repository(ABC, Generic[T, ID]):
    """
    Generic repository interface for CRUD operations

    Type Parameters:
        T: The type of the entity being managed by the repository.
        ID: The type of the identifier (defaults to Union[str, object])
    """

    @abstractmethod
    async def find_one(self, id: ID) -> T:
        """
        Retrieves a single entity based on the provided ID.

        Args:
            id: ID of the document/row to search

        Returns:
            Instance of one single object.
        """
        pass

    @abstractmethod
    async def find_all(self) -> List[T]:
        """
        Retrieves all entities as an array of objects.

        Returns:
            Instance of all objects.
        """
        pass

    @abstractmethod
    async def update_one(self, id: ID, entity: T) -> int:
        """
        Updates the entity associated with the provided ID.

        Args:
            id: ID of the entity to update
            entity: Updated object with the parameters

        Returns:
            Count of updated documents.
        """
        pass

    @abstractmethod
    async def delete_one(self, id: ID) -> bool:
        """
        Deletes the record for the provided ID.

        Args:
            id: ID of the record that has to be deleted from the table/collection.

        Returns:
            Acknowledgement of the deletion.
        """
        pass

    @abstractmethod
    async def create(self, entity: T) -> Union[str, object]:
        """
        Creates a new record based on the input parameter.

        Args:
            entity: Object property, as key-value pairs

        Returns:
            ID of the newly created record
        """
        pass

    @abstractmethod
    async def delete_all(self) -> int:
        """
        Deletes all records in the table/collection.

        Returns:
            Count of deleted records
        """
        pass
