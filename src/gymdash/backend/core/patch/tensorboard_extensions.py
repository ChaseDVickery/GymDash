try:
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    from tensorboard.backend.event_processing.reservoir import Reservoir, _ReservoirBucket
    _has_tensorboard = True
except ImportError:
    _has_tensorboard = False
    

def patch():

    if not _has_tensorboard:
        raise ImportError("tensorboard is required to patch tensorboard_extensions.")

    # _ReservoirBucket
    def Clear(self):
        with self._mutex:
            self.items.clear()
            self._num_items_seen = 0
    _ReservoirBucket.Clear = Clear
    del(Clear)


    # Reservoir
    def Clear(self, key):
        with self._mutex:
            bucket = self._buckets[key]
        old_len = len(bucket.items)
        bucket.Clear()
        print(f"Clearing Reservoir key={key}. {old_len} -> {len(bucket.items)} values")
    def Count(self, key):
        with self._mutex:
            bucket = self._buckets[key]
        return len(bucket.items)
    Reservoir.Clear = Clear
    Reservoir.Count = Count
    del(Clear)
    del(Count)


    # EventAccumulator
    def TensorsR(self):
        return self.tensors
    def CompressedHistogramsR(self):
        return self.compressed_histograms
    def HistogramsR(self):
        return self.histograms
    def ImagesR(self):
        return self.images
    def AudioR(self):
        return self.audio
    def ScalarsR(self):
        return self.scalars
    EventAccumulator.TensorsR = TensorsR
    EventAccumulator.CompressedHistogramsR = CompressedHistogramsR
    EventAccumulator.HistogramsR = HistogramsR
    EventAccumulator.ImagesR = ImagesR
    EventAccumulator.AudioR = AudioR
    EventAccumulator.ScalarsR = ScalarsR
    del(TensorsR)
    del(CompressedHistogramsR)
    del(HistogramsR)
    del(ImagesR)
    del(AudioR)
    del(ScalarsR)