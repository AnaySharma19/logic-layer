from logiclayer.connectors.nvidia_connector import NvidiaConnector

connector = NvidiaConnector()
response = connector.send("Say hello")
print(response)