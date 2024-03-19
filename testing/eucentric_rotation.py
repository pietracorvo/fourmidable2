import numpy as np

theta1 = 22.5
x1 = np.array((-1888, 3443))

theta2 = 25
x2 = np.array((-2094, 3282))


# theta3 = 55
# x3 = np.array((-2827.42, 2337.77))

def get_rot(angle):
    angle = np.radians(angle)
    c, s = np.cos(angle), np.sin(angle)
    R = np.array(((c, s), (-s, c)))
    return R


# R1 = get_rot(theta1)
# R2 = get_rot(theta2)
#
# r = np.linalg.inv(R2-R1).dot(R2.dot(x2)-R1.dot(x1))
# print(r)
#
# xT = R1.dot(x1-r)+r
#
# theta4 = 40
# print(np.linalg.inv(get_rot(theta4)).dot(xT-r)+r)
#
#
# theta0 = 22.5
# x0 = np.array((-1985, 2830))
# theta_wanted = 25
# print('move to: ')
# print(get_rot(theta0-theta_wanted).dot(x0-r)+r)


xt1 = np.array((-465, 3914))
th1 = 24
xt2 = np.array((-524, 3864))
th2 = 25
xt3 = np.array((-449, 3890))
th3 = 23
xt4 = np.array((-425, 3920))
th4 = 22.5

R1 = get_rot(-th2)
R2 = get_rot(-th4)
r = np.linalg.inv(R2-R1).dot(R2.dot(xt4)-R1.dot(xt2))
xs = R1.dot(xt2-r)+r
print('r: ', r)
print('xs: ', xs)

R3 = get_rot(th3)
xt3_calc = R3.dot(xs-r)+r
print(xt3_calc)
print(get_rot(24).dot(xs-r)+r)
