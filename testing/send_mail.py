import smtplib

from email.mime.text import MIMEText


s =smtplib.SMTP_SSL('smtp.gmail.com')
#Next, log in to the server
s.login("alphascorpii32@gmail.com", "AntAres11235813")

print('Login successful')

msg = MIMEText('blabla')       # create a message


# setup the parameters of the message
msg['From']='alphascorpii32@gmail.com'
msg['To']='lukaskoric32@gmail.com'
msg['Subject']="This is TEST"

for i in range(10):
    # Send the message via our own SMTP server.
    s.send_message(msg)
s.quit()
