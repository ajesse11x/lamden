

"""
----------------------------------------
Input Decorators
----------------------------------------

Input decorators allow states to define logic for incoming messages from the ReactorDaemon. These messages can be
envelopes from other actors, or timeout callbacks from unreceived replies.

# TODO more explanations
# TODO examples of how to use input decorators
"""


class StateInput:
    """
    A grouping of constants
    """
    INPUT = '_route_input'
    REQUEST = '_route_request'
    TIMEOUT = '_route_timeout'

    ALL = [INPUT, REQUEST, TIMEOUT]


def input(msg_type):
    def decorate(func):
        # func._recv = msg_type
        setattr(func, StateInput.INPUT, msg_type)
        return func
    return decorate


def input_request(msg_type):
    def decorate(func):
        # func._reply = msg_type
        setattr(func, StateInput.REQUEST, msg_type)
        return func
    return decorate


def timeout(msg_type):
    def decorate(func):
        # func._timeout = msg_type
        setattr(func, StateInput.TIMEOUT, msg_type)
        return func
    return decorate


"""
----------------------------------------
Transition Decorators
----------------------------------------

Transition decorators allow states to define logic surrounding state transitions. Methods can be decorated to execute
some code whenever the defining state is transition into from another state, using enter_state(...), or transitioned 
out of into another state, using exit_state(....).  

For either decorator enter_state(...)/exit_state(...), if no arguement is specified then that method will act as a 
'wildcard' and be called for ALL transitions, unless the state has another method that is decorated to handle a
a particular state.

# TODO clearer explanation
# TODO examples 
"""


# Internal constant for capturing all states using @enter_state and @exit_state decorators
ALL_STATES = 'ALL_STATES'


def _transition_state(handlers_attr: str, args):
    from cilantro.protocol.statemachine.state import State, StateMeta

    def decorate(func):
            if not states:
                print("configuring func {} to capture all states".format(func))
                # func._enter_handlers = states
            else:
                print("func {} configured to capture state {}".format(func, states))
                # func._enter_handlers = states

            # func._enter_handlers = states
            print("setting attr named {} on object {} to value {}".format(handlers_attr, func, states))
            setattr(func, handlers_attr, states)

            def _func(*args, **kwargs):
                print("entering func with args {} and kwargs {}".format(args, kwargs))
                func(*args, **kwargs)
                print("exiting func")

            return _func

    # Check if this decorator was used with args
    # if len(args) == 1 and callable(args[0]) and not issubclass(args[0], State):
    if len(args) == 1 and callable(args[0]) and not ((type(args[0]) is StateMeta) and issubclass(args[0], State)):
        print("this method was not decorated")
        states = ALL_STATES
        return decorate(args[0])
    else:
        print("entry method was decorated with args {}!!!".format(args))
        # TODO validate states are actually state subclasses
        states = args
        return decorate


def enter_state(*args):
    return _transition_state(handlers_attr='_enter_handlers', args=args)


def exit_state(*args):
    return _transition_state(handlers_attr='_exit_handlers', args=args)

