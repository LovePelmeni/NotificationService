import pika.exceptions, io


class RabbitmqConnection(object):
    """
    / * Class Represents rabbitmq Connection in the current service.
    // * Use simple pika client connection as an implementation
    """

    def __call__(self, *args, **kwargs):
        return self.connect_to_server()

    def connect_to_server(self):
        pass

    def publish_event(self):
        pass

    def listen_event(self):
        pass


class TransactionListener(object):

    """
    / * Class Listen for incoming transactions from other services.
    // * Implements Part of the SAGA Pattern, Locally in the Service
    """

    def __call__(self, *args, **kwargs):
        pass

    def listen_for_response(self):
        pass

    def listen_for_request(self):
        pass

    def send_request(self):
        pass





