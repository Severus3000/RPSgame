import time

def function1():
    print(time.time())
    time.sleep(1)
    print(1)

def function2():
    time.sleep(2)
    print(2)
    print(time.time())

def function3():
    print(3)
    print(time.time())

async def function4():
    print(time.time())
    time.sleep(1)
    print(1)

async def function5():
    time.sleep(2)
    print(2)
    print(time.time())

async def function6():
    print(3)
    print(time.time())  

function1()
function2()
function3()
function4()
function5()
function6()  

