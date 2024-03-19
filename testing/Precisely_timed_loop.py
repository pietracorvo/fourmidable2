import time as tm


def acusleep(t):
    counter = 0
    now = tm.clock()
    check = 0
    while check < now+t:
        check = tm.clock()
        counter += 1
    print(counter)

start = tm.clock()  #Store precise version of time

for a in range(15):
    print('----------')
    print(a+1)
    now = tm.clock()
    print(tm.clock())
    tm.sleep((a+1)-now)
    print('---instant----')
    print(tm.clock())
    print(tm.clock())
    print('--- Sleep 2ms wait----')
    print(tm.clock())
    tm.sleep(2/1000)
    print(tm.clock())
    print('---acusleep 2ms wait----')
    print(tm.clock())
    acusleep(0.002)
    print(tm.clock())

