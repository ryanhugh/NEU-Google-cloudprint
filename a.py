import traceback

try:
    raise ValueError
except:
    tb = traceback.format_exc()

print 'hi'
print tb
