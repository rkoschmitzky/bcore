#-*-coding:utf-8-*-
"""
@package bcore.tests.core.kvstore.test_properties
@brief tests for bcore.core.kvstore.properties

@copyright 2012 Sebastian Thiel
"""
__all__ = []

from bcore.tests.core.component.base import TestComponentCoreBase
from bcore.core.component import *
from bcore.core.kvstore import RootKey
from bcore.path import Path


## [ExampleContextClient]

class ExampleContextClient(PropertyEnvironmentStackContextClient):
    __slots__ = ()
    
    site = CompoundPropertyDescriptor(ContextPropertyDescriptor(name='id', type=str),
                                      CompoundPropertyDescriptor(
                                            ContextPropertyDescriptor(name='repository', type=Path),
                                            name='root_path'
                                      ))

## [ExampleContextClient]
# end class ExampleContextClient


class TestEnvironmentProperties(TestComponentCoreBase):
    __slots__ = ()

    def test_base(self):
        """Test functionality of KVStore properties"""
        client = ExampleContextClient()
        assert client.schema().key() == RootKey
        assert issubclass(client.schema().site.id, str)
        
        assert not client.has_value_cache()
        assert client.clear_value_cache() is client, 'clear without having cache is no problem'
        assert client.value_cache(), "should have obtained some value"
        assert client.has_value_cache()
        client.clear_value_cache()
        assert not client.has_value_cache(), "shouldn't have value cache after clearing it"
        
        ## [ExampleContextClient Usage]
        assert len(client.site) == 2
        assert isinstance(client.site.id, str)
        assert isinstance(client.site.root_path.repository, Path)
        ## [ExampleContextClient Usage]
        
        assert client.has_value_cache(), "Properties auto-retrieve the cache"
