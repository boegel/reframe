#
# Decorators for registering tests with the framework
#

__all__ = ['parameterized_test', 'simple_test', 'required_version']


import collections
import inspect
import traceback

import reframe
from reframe.core.exceptions import ReframeSyntaxError
from reframe.core.logging import getlogger
from reframe.core.pipeline import RegressionTest
from reframe.utility.versioning import Version, VersionValidator


def _register_test(cls, args=None):
    def _instantiate():
        ret = []
        for cls, args in mod.__rfm_test_registry:
            try:
                if cls in mod.__rfm_skip_tests:
                    continue

            except AttributeError:
                mod.__rfm_skip_tests = set()

            try:
                if isinstance(args, collections.Sequence):
                    ret.append(cls(*args))
                elif isinstance(args, collections.Mapping):
                    ret.append(cls(**args))
                elif args is None:
                    ret.append(cls())
            except Exception as e:
                getlogger().error('%s:%s: skipping due to errors; check log'
                                  'file for more information.' %
                                  (inspect.getfile(cls), cls.__name__))
                getlogger().debug(traceback.format_exc())

        return ret

    mod = inspect.getmodule(cls)
    if not hasattr(mod, '_rfm_gettests'):
        mod._rfm_gettests = _instantiate

    try:
        mod.__rfm_test_registry.append((cls, args))
    except AttributeError:
        mod.__rfm_test_registry = [(cls, args)]


def _validate_test(cls):
    if not issubclass(cls, RegressionTest):
        raise ReframeSyntaxError('the decorated class must be a '
                                 'subclass of RegressionTest')


def simple_test(cls):
    """Class decorator for registering parameterless tests with ReFrame.

    The decorated class must derive from
    :class:`reframe.core.pipeline.RegressionTest`.  This decorator is also
    available directly under the :mod:`reframe` module.

    .. versionadded:: 2.13

    """

    _validate_test(cls)
    _register_test(cls)
    return cls


def parameterized_test(*inst):
    """Class decorator for registering multiple instantiations of a test class.

   The decorated class must derive from
   :class:`reframe.core.pipeline.RegressionTest`. This decorator is also
   available directly under the :mod:`reframe` module.

   :arg inst: The different instantiations of the test. Each instantiation
        argument may be either a sequence or a mapping.

   .. versionadded:: 2.13

   .. note::

      This decorator does not instantiate any test.  It only registers them.
      The actual instantiation happens during the loading phase of the test.

    """
    def _do_register(cls):
        _validate_test(cls)
        for args in inst:
            _register_test(cls, args)

        return cls

    return _do_register


def required_version(*versions):
    """Class decorator for specifying the required ReFrame versions for the
    following test.

    If the test is not compatible with the current ReFrame version it will be
    skipped.

    :arg versions: A list of ReFrame version specifications that this test is
      allowed to run. A version specification string can have one of the
      following formats:

      1. ``VERSION``: Specifies a single version.

      2. ``{OP}VERSION``, where ``{OP}`` can be any of ``>``, ``>=``, ``<``,
      ``<=``, ``==`` and ``!=``. For example, the version specification string
      ``'>=2.15'`` will only allow the following test to be loaded only by
      ReFrame 2.15 and higher. The ``==VERSION`` specification is the
      equivalent of ``VERSION``.

      3. ``V1..V2``: Specifies a range of versions.

      You can specify multiple versions with this decorator, such as
      ``@required_version('2.13', '>=2.16')``, in which case the test will be
      selected if *any* of the versions is satisfied, even if the versions
      specifications are conflicting.

    .. versionadded:: 2.13

    """
    if not versions:
        raise ValueError('no versions specified')

    conditions = [VersionValidator(v) for v in versions]

    def _skip_tests(cls):
        mod = inspect.getmodule(cls)
        if not hasattr(mod, '__rfm_skip_tests'):
            mod.__rfm_skip_tests = set()

        if not any(c.validate(reframe.VERSION) for c in conditions):
            getlogger().info('skipping incompatible test defined'
                             ' in class: %s' % cls.__name__)
            mod.__rfm_skip_tests.add(cls)

        return cls

    return _skip_tests
