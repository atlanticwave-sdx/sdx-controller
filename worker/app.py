""" rabit mq worker process """
import time
import pika

SLEEP_TIME = 5
print(' [*] Sleeping for ', SLEEP_TIME, ' seconds.')
time.sleep(SLEEP_TIME)

print(' [*] Connecting to server ...')
credentials = pika.PlainCredentials('mq_user', 'mq_pwd')
connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq3', 5672, '/', credentials))
channel = connection.channel()
channel.queue_declare(queue='task_queue', durable=True)

print(' [*] Waiting for messages.')


def callback(call_channel, method, properties, body):
    """ call back """
    print(f" [x] Received {body}")
    cmd = body.decode()

    if cmd == 'hey':
        print("hey there")
    elif cmd == 'hello':
        print("well hello there")
    else:
        print("sorry i did not understand ", body)

    print(" [x] Done")

    call_channel.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='task_queue', on_message_callback=callback)
channel.start_consuming()
