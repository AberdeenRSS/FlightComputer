class IDataAge:

    def get_data_age(self) -> float | None:
        '''
        Returns the timestamp of the data creation in unix seconds
        Returns None if no data was received yet
        '''
        return None