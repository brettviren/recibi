
def string_match(key, entry, matches):
    '''
    Match key fields of entry against matches, list of (field,regex).
    '''
    for name, pattern in matches:
        if name == "key":
            val = key
        else:
            try:
                val = entry.fields[name]
            except KeyError:
                return False
        if not re.search(pattern, val, re.IGNORECASE):
            return False
    return True


def test_number(val, op):
    # Using eval is not the best thing....
    code = f'{val}{op}'
    return eval(code)


def number_match(key, entry, matches):
    '''
    Match key and fields of entry against matches as numerical operation.
    '''
    for name, test in matches:
        if name == "key":
            if not test_number(test, key):
                return False
        try:
            val = entry.fields[name]
        except KeyError:
            return False

        if not test_number(val, test):
            return False
    return True

