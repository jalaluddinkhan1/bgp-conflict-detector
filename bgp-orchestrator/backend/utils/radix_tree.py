"""
Efficient prefix lookup using radix tree (patricia trie).
"""
from typing import Any, Iterator, Optional, Tuple


class RadixNode:
    """Node in the radix tree."""

    def __init__(self, prefix: str = "", value: Any = None):
        self.prefix = prefix
        self.value = value
        self.children: dict[str, "RadixNode"] = {}
        self.is_leaf = value is not None


class RadixTree:
    """
    Radix tree (Patricia trie) for efficient prefix lookup.
    
    Useful for longest prefix matching in BGP routing tables.
    """

    def __init__(self):
        self.root = RadixNode()

    def insert(self, prefix: str, value: Any) -> None:
        """
        Insert a prefix into the tree.
        
        Args:
            prefix: Prefix string (e.g., "192.0.2.0/24")
            value: Value to store for this prefix
        """
        self._insert_recursive(self.root, prefix, value, 0)

    def _insert_recursive(
        self, node: RadixNode, prefix: str, value: Any, index: int
    ) -> None:
        """Recursive helper for insert."""
        if index >= len(prefix):
            node.value = value
            node.is_leaf = True
            return

        char = prefix[index]
        if char not in node.children:
            node.children[char] = RadixNode(prefix[index:], value)
            node.children[char].is_leaf = True
        else:
            child = node.children[char]
            # Find common prefix
            common_len = 0
            min_len = min(len(child.prefix), len(prefix) - index)
            for i in range(min_len):
                if child.prefix[i] == prefix[index + i]:
                    common_len += 1
                else:
                    break

            if common_len == len(child.prefix):
                # Continue with child
                self._insert_recursive(child, prefix, value, index + common_len)
            else:
                # Split node
                split_node = RadixNode(child.prefix[common_len:], child.value)
                split_node.children = child.children
                split_node.is_leaf = child.is_leaf

                child.prefix = child.prefix[:common_len]
                child.value = None
                child.is_leaf = False
                child.children = {split_node.prefix[0]: split_node}

                if index + common_len < len(prefix):
                    new_node = RadixNode(prefix[index + common_len:], value)
                    new_node.is_leaf = True
                    child.children[prefix[index + common_len]] = new_node
                else:
                    child.value = value
                    child.is_leaf = True

    def search(self, prefix: str) -> Optional[Any]:
        """
        Search for exact prefix match.
        
        Args:
            prefix: Prefix to search for
            
        Returns:
            Value if found, None otherwise
        """
        node = self._search_node(prefix)
        return node.value if node and node.is_leaf else None

    def longest_prefix_match(self, key: str) -> Optional[Tuple[str, Any]]:
        """
        Find longest prefix match for a given key.
        
        Args:
            key: Key to search for
            
        Returns:
            Tuple of (prefix, value) if found, None otherwise
        """
        result = None
        node = self.root
        matched_prefix = ""

        for char in key:
            if char not in node.children:
                break
            node = node.children[char]
            matched_prefix += node.prefix

            if node.is_leaf:
                result = (matched_prefix, node.value)

        return result

    def _search_node(self, prefix: str) -> Optional[RadixNode]:
        """Search for a node matching the prefix."""
        node = self.root
        index = 0

        while index < len(prefix) and node:
            char = prefix[index]
            if char not in node.children:
                return None

            node = node.children[char]
            node_prefix_len = len(node.prefix)

            # Check if node prefix matches
            if index + node_prefix_len > len(prefix):
                return None

            if prefix[index : index + node_prefix_len] != node.prefix:
                return None

            index += node_prefix_len

        return node if index == len(prefix) else None

    def delete(self, prefix: str) -> bool:
        """
        Delete a prefix from the tree.
        
        Args:
            prefix: Prefix to delete
            
        Returns:
            True if deleted, False if not found
        """
        return self._delete_recursive(self.root, prefix, 0)

    def _delete_recursive(self, node: RadixNode, prefix: str, index: int) -> bool:
        """Recursive helper for delete."""
        if index >= len(prefix):
            if node.is_leaf:
                node.value = None
                node.is_leaf = False
                return True
            return False

        char = prefix[index]
        if char not in node.children:
            return False

        child = node.children[char]
        if self._delete_recursive(child, prefix, index + len(child.prefix)):
            # Clean up empty nodes
            if not child.is_leaf and not child.children:
                del node.children[char]
            return True

        return False

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        """Iterate over all prefixes and values."""
        yield from self._iter_recursive(self.root, "")

    def _iter_recursive(
        self, node: RadixNode, prefix: str
    ) -> Iterator[Tuple[str, Any]]:
        """Recursive helper for iteration."""
        current_prefix = prefix + node.prefix
        if node.is_leaf:
            yield (current_prefix, node.value)

        for child in node.children.values():
            yield from self._iter_recursive(child, current_prefix)

    def __len__(self) -> int:
        """Get number of prefixes in the tree."""
        return sum(1 for _ in self)

