# tutorial based of freeCodeCamp.org
# https://www.youtube.com/watch?v=XGf2GcyHPhc&ab_channel=freeCodeCamp.org
# adapted by @basgonclaves

import turtle
import time
from PIL import Image
from matplotlib.ft2font import BOLD
import os

height_window = 600
width_window = 800
paddle_x_position = 350
pixelspersecond = 0.1                         # delta x /speed of the ball ( change if needed depending on the computer)
bounncing_state= 0

wn = turtle.Screen()
wn.title('Pong by @basgoncalves')
wn.bgcolor('black')
wn.setup(width_window,height_window)
wn.tracer(0)

current_file = __file__
ogPicPath = os.path.join(current_file,'..\\opensim.jpg')
picPongPath = os.path.join(current_file,'..\\opensim.gif')

image = Image.open(ogPicPath)
new_image = image.resize((50, 50))
new_image.save(picPongPath)

wn.addshape(picPongPath)

# Paddel A
paddle_a = turtle.Turtle()
paddle_a.speed(0)
paddle_a.shape('square')
paddle_a.color('white')
paddle_a.penup()
paddle_a.goto(-paddle_x_position,0)
paddle_a.shapesize(5,1,1)

# Paddel B
paddle_b = turtle.Turtle()
paddle_b.speed(0)
paddle_b.shape('square')
paddle_b.color('white')
paddle_b.penup()
paddle_b.goto(paddle_x_position,0)
paddle_b.shapesize(5,1,1)

# Ball 
ball = turtle.Turtle()
ball.speed(0)
ball.shape(picPongPath)
ball.color('red')
ball.penup()
ball.goto(0,0)
ball.dx = pixelspersecond 
ball.dy = pixelspersecond

# socre 
score_a = 0
score_b = 0

# pen 
pen = turtle.Turtle()
pen.speed (0)
pen.color('white')
pen.penup()
pen.hideturtle()
pen.goto(0,height_window*0.4)


# Fucntions
def paddle_a_up():
    y = paddle_a.ycor()
    y += 20
    paddle_a.sety(y)

def paddle_a_down():
    y = paddle_a.ycor()
    y -= 20
    paddle_a.sety(y)

def paddle_b_up():
    y = paddle_b.ycor()
    y += 20
    paddle_b.sety(y)

def paddle_b_down():
    y = paddle_b.ycor()
    y -= 20
    paddle_b.sety(y)

def updateScore():
    pen.clear()
    pen.write('Payer A : {} Player B: {}'.format(score_a,score_b), align='center',font=('console',20, 'bold'))

updateScore()

wn.listen()
wn.onkeypress(paddle_a_up, 'w')
wn.onkeypress(paddle_a_down, 's')
wn.onkeypress(paddle_b_up, 'Up')
wn.onkeypress(paddle_b_down, 'Down')

#main game loop
while True:
    wn.update()

    # ball movement 
    ball.setx(ball.xcor() + ball.dx)
    ball.sety(ball.ycor() + ball.dy)

    # y border check
    margin = 310
    if ball.ycor() > height_window-margin:
        ball.sety(height_window-margin)
        ball.dy *= -1
    
    if ball.ycor() < -height_window+margin:
        ball.sety(-height_window+margin)
        ball.dy *= -1

    # x border check
    if ball.xcor() > width_window-margin:
        ball.goto(0,0)
        ball.dx *= -1
        score_a += 1
        updateScore()
    
    if ball.xcor() < -width_window+margin:
        ball.goto(0,0)
        ball.dx *= -1
        score_b += 1
        updateScore()

    # contact with the paddels mechanisms
    width_paddel = 20
    if (ball.xcor() < -paddle_x_position+width_paddel and ball.xcor() > -paddle_x_position-width_paddel) and (ball.ycor() < paddle_a.ycor() + 60) and (ball.ycor() > paddle_a.ycor() - 60) and bounncing_state == 0:
        ball.dx *= -1
        bounncing_state = 1
    else:
        bounncing_state = 0

    if (ball.xcor() > paddle_x_position-width_paddel and ball.xcor() < paddle_x_position+width_paddel) and (ball.ycor() < paddle_b.ycor() + 60) and (ball.ycor() > paddle_b.ycor() - 60) and bounncing_state == 0:
        ball.dx *= -1
        bounncing_state = 1
    else:
        bounncing_state = 0
