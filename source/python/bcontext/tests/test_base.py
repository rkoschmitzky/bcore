#-*-coding:utf-8-*-
"""
@package bcore.tests.component.test_base
@brief Test for bcore.component.base

@copyright 2012 Sebastian Thiel
@todo get rid of the standard error redirect or maybe solve it differently
"""
__all__ = []

import abc

import bcore
from bcore.tests import swap_globals
from bcore.tests.component.base import TestComponentCoreBase
# test wildcard import
# pylint: disable=W0614
from bcore.component import *
# pylint: enable=W0614


class TestGlobalsSwitching(TestComponentCoreBase):
    def test_switch(self):
        env_name_001 = "env001"
        env_name_002 = "env002"
        test_arg = "foo"

        class I1s(bcore.InterfaceBase):
            def echo(self, arg1):
                pass

        class I2s(bcore.InterfaceBase):
            pass

        bcore.environment.push(env_name_001)

        class P1s(I1s, Plugin):
            def echo(self, arg1):
                return arg1

        P1s()

        p1 = bcore.environment.services(I1s)
        assert(len(p1) == 1)
        assert(p1[0].echo(test_arg) == test_arg)

        # switch environment stack
        new_env = EnvironmentStack()
        saved_env = swap_globals(new_env)

        # we're in a new environment stack, so P1s from above should be gone
        assert not bcore.environment.services(I1s)

        bcore.environment.push(env_name_002)

        class P2s(I2s, Plugin):
            pass
        P2s()

        p2 = bcore.environment.services(I2s)
        assert(len(p2) == 1)

        # switch back to the saved environment stack
        swap_globals(saved_env)

        # so we want to find the P1s again
        p1 = bcore.environment.services(I1s)
        assert(len(p1) == 1)
        assert(p1[0].echo(test_arg) == test_arg)

        # but the P2s should be gone
        assert not bcore.environment.services(I2s)


class TestEnvironmentStack(TestComponentCoreBase):
    saved_globals = None
    test_globals  = EnvironmentStack()
    def setUp(self):
        self.saved_globals = swap_globals(self.test_globals)
        bcore.environment.reset()

    def tearDown(self):
        bcore.environment.reset()
        swap_globals(self.saved_globals)

    def test_empty_stack(self):

        assert(len(bcore.environment) == 1)

    def test_push(self):
        env_name = "env001"
        # test normal push
        bcore.environment.push(env_name)
        assert(len(bcore.environment) == 2)
        assert(bcore.environment.top().name() == env_name)

    def test_pop(self):
        env_name = "env002"
        # what we push we should get back with pop
        plen = len(bcore.environment)
        assert plen == 1
        bcore.environment.push(env_name)
        assert len(bcore.environment) == plen + 1
        assert(bcore.environment.pop().name() == env_name)
        assert(len(bcore.environment) == 1)
        # if the stack is down to the base env, we don't get anything pop()'d
        self.failUnlessRaises(ValueError, bcore.environment.pop)
        assert(len(bcore.environment) == 1)

    def test_replace(self):
        replace_name = "env004"
        tos_name     = "env003"
        bcore.environment.push("env001")
        bcore.environment.push("env002")
        bcore.environment.push(tos_name)
        bcore.environment.replace(lambda env: env.name() == "env002", replace_name)
        assert(bcore.environment.top().name() == tos_name)
        bcore.environment.pop()
        assert(bcore.environment.top().name() == replace_name)

    def test_replace_match(self):
        category = 'host_application'
        houdini_env_name = 'houdini'
        class MayaEnvironment(Environment):
            _category = category
            def __init__(self, name):
                super(MayaEnvironment, self).__init__(name)

        class HoudiniEnvironment(Environment):
            _category = category
            def __init__(self, name):
                super(HoudiniEnvironment, self).__init__(name)

        maya_env    = MayaEnvironment("maya")
        houdini_env = HoudiniEnvironment(houdini_env_name)

        bcore.environment.push("base")
        bcore.environment.push(maya_env)
        bcore.environment.push("top")
        prev_len = len(bcore.environment)
        bcore.environment.replace(lambda env: env.category() == category, houdini_env)
        assert len(bcore.environment) == prev_len, "replacements shouldn't change the stack size"
        bcore.environment.pop()
        assert(bcore.environment.top().name() == houdini_env_name)

    def test_find_env(self):
        env001   = "env001"
        category = "test"
        class TestEnvironment(Environment):
            _category = category

        bcore.environment.push(TestEnvironment(env001))
        bcore.environment.push("env002")
        env = bcore.environment._find_env(lambda env: env.name() == env001)
        assert(env.name() == env001)
        env = bcore.environment._find_env(lambda env: env.category() == category)
        assert(env.name() == env001)
        env = bcore.environment._find_env(lambda x: type(x) is type(env))
        assert(env.name() == env001)

    def test_context(self):
        category = 'host_application'
        bottom_env_name  = 'bottom'
        maya_env_name    = 'maya'
        maya_version     = 'maya 2012'
        houdini_env_name = 'houdini'
        houdini_version  = 'houdini 23'
        top_env_name     = 'top'
        key_category = 'environment.category'
        key_name = 'environment.name'
        key_version = 'host_application.version'
        
        class TestContextEnvironment(Environment):
            _category = category
            def __init__(self, name):
                super(TestContextEnvironment, self).__init__(name)
                self._kvstore.set_value('environment.name', self.name())
                self._kvstore.set_value('environment.category', self.category())
                
        class MayaEnvironment(TestContextEnvironment):
            def __init__(self, name):
                super(MayaEnvironment, self).__init__(name)
                self._kvstore.set_value("host_application.version", maya_version)

        class HoudiniEnvironment(TestContextEnvironment):
            def __init__(self, name):
                super(HoudiniEnvironment, self).__init__(name)
                self._kvstore.set_value("host_application.version", houdini_version)

        maya_env    = MayaEnvironment(maya_env_name)
        houdini_env = HoudiniEnvironment(houdini_env_name)

        ctx = bcore.environment.context()
        assert(not ctx.keys())
        bcore.environment.push(bottom_env_name)
        ctx = bcore.environment.context()
        assert(not ctx.keys())
        bcore.environment.push(maya_env)
        ctx = bcore.environment.context()
        assert(ctx.value(key_category, '') == category)
        assert(ctx.value(key_name, '') == maya_env_name)
        assert(ctx.value(key_version, 'X') == maya_version)
        bcore.environment.push("top")
        ctx = bcore.environment.context()
        assert(ctx.value(key_category, '') == category)
        assert(ctx.value(key_name, '') == maya_env_name)
        assert(ctx.value(key_version, 'X') == maya_version)
        assert bcore.environment.replace(lambda env: env.category() == category, houdini_env) is maya_env
        ctx = bcore.environment.context()
        assert(ctx.value(key_category, '') == category)
        assert(ctx.value(key_name, '') == houdini_env_name)
        assert(ctx.value(key_version, 'X') == houdini_version)
        bcore.environment.pop()
        ctx = bcore.environment.context()
        assert(ctx.value(key_category, '') == category)
        assert(ctx.value(key_name, '') == houdini_env_name)
        assert(ctx.value(key_version, 'X') == houdini_version)
        bcore.environment.pop()
        ctx = bcore.environment.context()
        assert(not ctx.keys())
        bcore.environment.pop()
        ctx = bcore.environment.context()
        assert(not ctx.keys())
        
    def test_instance(self):
        env_name = "env001"
        class MyEnvironment(Environment):
            def __init__(self):
                super(MyEnvironment, self).__init__(env_name)

        env = MyEnvironment()

        bcore.environment.push(env)

        assert(bcore.environment.top().name() == env_name)

# end class TestEnvironmentStack

class TestPlugin(TestComponentCoreBase):
    saved_globals = None

    def setUp(self):
        new_globals = EnvironmentStack()
        self.saved_globals = swap_globals(new_globals)
        assert bcore.environment is new_globals
        bcore.environment.reset(new_base=True)
        
    def tearDown(self):
        bcore.environment.reset(new_base=True)
        swap_globals(self.saved_globals)

    def test_implements(self):
        class I1(bcore.InterfaceBase):
            def func(self, arg1):
                pass

        bcore.environment.push("env001")

        class P1(I1, Plugin):
            def func(self, arg1):
                pass

        classes = bcore.environment.top()._classes(I1)
        assert(len(classes) == 1)
        cls = classes[0]
        assert(cls.__module__ == __name__)
        assert(cls.__name__ == "P1")
        
        # Test builtins ... its a mess here, but lets go with it for now
        self.failUnlessRaises(ServiceNotFound, service, TestComponentCoreBase)
        P1()
        assert isinstance(service(I1), P1)

    def test_implements_inherits(self):
        test_arg = 'foo'
        class I1ii(bcore.InterfaceBase):
            def echo(self, arg1):
                return arg1

        class I2ii(I1ii):
            pass

        bcore.environment.push("env001")

        # P1 inherits from I2, I2 inherits from I1, I1 has the echo functions tested for below
        class P1ii(I2ii, Plugin):
            def echo(self, arg1):
                return "foo"

        P1ii()

        svcs = bcore.environment.services(I2ii)
        assert(len(svcs) == 1)
        assert(svcs[0].echo(test_arg) == "foo")

    def test_inheritance_excpetion(self):
        class I1ie(bcore.InterfaceBase):
            def echo(self, arg1):
                return arg1

        class I2ie(I1ie):
            pass

        bcore.environment.push("env001")

        class P1ie(I1ie, Plugin):
            pass
                
        class I2(bcore.InterfaceBase):
            pass
        
        # multi-inheritance
        class P2(I2, P1ie):
            pass
        
    def test_find_services(self):
        test_arg = 'foo'

        # interfaces
        class Inix(bcore.InterfaceBase):
            pass
        class I0(bcore.InterfaceBase):
            pass
        class I1(bcore.InterfaceBase):
            @abc.abstractmethod
            def echo(self, arg1):
                pass

        bcore.environment.push("env001")

        class P1(I1, Plugin):
            def echo(self, arg1):
                return arg1

        class P01(I0, I1, Plugin):
            def echo(self, arg1):
                return arg1

        class P0(I0, Plugin):
            pass

        P1()

        # don't find services that don't exist
        assert not bcore.environment.services(Inix)

        # do find the one service that exists for I1
        p1 = bcore.environment.services(I1)
        assert(len(p1) == 1)
        assert(p1[0].echo(test_arg) == test_arg)

        bcore.environment.push("env002")
        # find the service below us
        p1 = bcore.environment.services(I1)
        assert(len(p1) == 1)
        assert(p1[0].echo(test_arg) == test_arg)

        P1()

        # we find 1 here
        p1 = bcore.environment.services(I1)
        assert(len(p1) == 1)
        assert(p1[0].echo(test_arg) == test_arg)
        # and 2 here
        p1 = bcore.environment.services(I1, traversal_mode=bcore.environment.RECURSE_ALWAYS)
        assert(len(p1) == 2)
        assert(p1[0].echo(test_arg) == test_arg)
        assert(p1[1].echo(test_arg) == test_arg)

        p01 = P01()
        P0()
        # this should find all the services we created so far
        assert(len(bcore.environment.services(None, traversal_mode = bcore.environment.RECURSE_ALWAYS)) == 4)

        bcore.environment.pop()
        # now we should only find the one service we created in env001
        p1 = bcore.environment.services(None)
        assert(len(p1) == 1)

        bcore.environment.push("env003")
        class P2(I1, Plugin):
            def echo(self, arg1):
                return arg1

        # there's no I1 service in the current environment
        assert len(bcore.environment.services(I1)) == 1
        p1 = bcore.environment.new_services(I1, predicate = CreateMissing)
        bcore.environment.new_services(I1, predicate = CreateMissing)
        assert(len(p1) == 3) # so the above should have created one
        # doing it again will not create more
        p1 = bcore.environment.new_services(I1, predicate = CreateMissing)
        assert(len(p1) == 3)
        assert(p1[0].echo(test_arg) == test_arg)

        bcore.environment.pop()
        bcore.environment.push("env004")
        p1 = bcore.environment.services(I1)
        assert(len(p1) == 1)
        p1 = bcore.environment.new_services(I1, predicate = CreateFirst)
        assert len(p1) == 1, "since it should have found the plugin from env001, it shouldn't create anything"
        assert(p1[0].echo(test_arg) == test_arg)
        p1 = bcore.environment.new_services(I1, predicate = CreateMissing)
        assert len(p1) == 2, "we had P1, but not P01, so that should have been created now"
        p1 = bcore.environment.new_services(I1, predicate = CreateMissing)
        assert len(p1) == 2, "and now nothing new should have been created"
        
        # new services - no ownership
        assert len(services(None)) == 1
        assert new_services(I1)
        assert len(services(None)) == 1
        
        # just make the call
        bcore.environment._contents_str()
        
    def test_duplicate_prevention(self):
        """assure we do not put in duplicates for interfaces"""
        assert not bcore.environment.top().services()
        class P1(Plugin):
            pass
        
        class P2(Plugin):
            pass
        
        assert len(bcore.environment.top()._registry) == 2, "Should have exactly 2 types"

    def test_component_architecture_demo(self):
        """A test done to demonstrate some basic features
        @todo put it into doc/test_examples and use it in doxygen"""
        # from bcore.interfaces import IPublish
        class IPublish(bcore.InterfaceBase):
            """docstring for IPublish"""
            
            @bcore.abstractmethod
            def publish(self, file):
                """@return True if the file was published"""
                pass

        class DefaultPublish(IPublish, Plugin):
            def publish(self, file):
                print "pipeline publish done"
                return True

        DefaultPublish()

        class ShotPublish(DefaultPublish):
            def __init__(self, arg):
                pass
            def publish(self, file):
                if file == "foo":
                    return False
                return super(ShotPublish, self).publish(file)

        # SINGLETONs
        ShotPublish(1)

        pbl = service(IPublish)
        assert pbl.publish("bar") == True
        assert pbl.publish("foo") == False

        count = 0
        for pbl in services(IPublish):
            pbl.publish("foo")
            count += 1
        assert count == 2



        # NEW SERVICE
        class ICheck(bcore.InterfaceBase):
            def __init__(self, arg):
                pass

            def check(self):
                return True

        class ModelCheck(ICheck, Plugin):
            def __init__(sefl, arg, kwarg=None):
                pass

            def check(self):
                return False

        check = new_service(ICheck, "foo")
        check2 = new_service(ModelCheck, "bar", kwarg=2)
        assert check is not check2
        self.failUnlessRaises(ServiceNotFound, service, ICheck)
        
        # Test Validation
        validator = bcore.environment.schema_validator()
        assert len(validator) == 1, 'should just have the default schema'
        assert len(validator.validate_schema()[1]) == 0, "default schema's should be empty"

    def test_loader(self):
        """Verify fundamental loader features"""
        module = PluginLoader.load_file(self.fixture_path('plugin.py'), 'test_plugin')
        assert module is not None and hasattr(module, 'MyDynamicPlugin')
        
        self.failUnlessRaises(AssertionError, PluginLoader.load_file, self.fixture_path('plugin_fail.py'), 'doesnt-matter')
        self.failUnlessRaises(IOError, PluginLoader.load_file, self.fixture_path('doesntexist.py'), 'doesnt-matter')

# end class TestPlugin