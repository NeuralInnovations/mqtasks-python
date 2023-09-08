# Message Queue Tasks

This module provides a framework for handling and processing asynchronous tasks through message queues.

---
## Overview
- Utilizes the **aio_pika** library for **AMQP** message processing.
- Offers easy-to-use decorators and methods for defining tasks, producing and consuming them.
- Built with asynchronous patterns to allow seamless scalability.

--- 
## Requirements
- Python **3.11+**
- **aio_pika** library
- **RabbitMQ** or other **AMQP** broker

---
## Usage

### 1. Defining a Task
To define a task, instantiate the MqTasks object and use the task decorator:
```python
import mqtasks

mq_tasks = MqTasks(amqp_connection="amqp://localhost", queue_name="my_queue")

@mq_tasks.task(name="my_task")
def my_task_function(ctx: MqTaskContext):
    # Process task
    pass

mq_tasks.run()
```

### 2. Sending a Task
Instantiate MqTasksClient and use it to send a task:

```python
import asyncio
import mqtasks

client = MqTasksClient(
    loop=asyncio.get_event_loop(),
    amqp_connection="amqp://localhost"
)

# define channel
channel = await client.queue(queue_name="my_queue")

#
result = await channel.run_task_async(task_name="my_task", body={"message":"hello world"})

```
---
## Examples:

#### How to start example:
- Work dir: ```./example```
  - ```cd ./example```
- Start **RabbitMQ**
  1. ```docker pull rabbitmq:management```
  2.  ```docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management```
- Access the **RabbitMQ** management web UI:
  - ```http://localhost:15672/```
- By default, the credentials are:
  - Username: **guest**
  - Password: **guest**
- **Server**
  - ```python example_server.py```
- **Client**
  - ```python example_client.py```
---
## License
MIT License