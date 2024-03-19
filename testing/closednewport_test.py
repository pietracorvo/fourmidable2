from control.instruments.moke import Moke
import time

if __name__ == '__main__':
    moke = Moke()
    try:
        ls = moke.instruments['Stage'].instruments['LinearStage']
        position = ls.get_position()
        position[1] += 20
        print('Increasing x by 20')
        ls.set_position(position)

        while ls.is_moving():
            time.sleep(0.5)
        print('Done first movement!')

        time.sleep(2)
        position[1] -= 20
        print('Decreasing x by 20')
        ls.set_position(position)
        while ls.is_moving():
            time.sleep(0.5)
    finally:
        print('Stopping moke')
        moke.stop()
