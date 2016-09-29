def callee_a():
    pass

def callee_b():
    callee_c()

def callee_c():
    pass

def caller():
   callee_a()
   callee_b()
   callee_a()

while True:
    caller()
