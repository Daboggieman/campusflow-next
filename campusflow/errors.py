"""
type of errors in the campusflow application.

there are two error families and they are deliberately kept apart to help with debugging and future
implementation

ValidationError
    these are errors caused by user action breaking the application rule eg 
    a blank title, an unacceptable urgency, inserting a string where an integer is expected or vice versa. 
    
DataErro
    broken stored data or stored datathat cannot be trusted e.g an unreadable JSON file, a duplicate ticket id,
    a record that fails validation.

"""


class ValidationError(ValueError):
    """A user action broke a rule. The caller may recover and continue."""

class DataError(Exception):
    """stored data is unusable. callers must keep their current state intact."""
