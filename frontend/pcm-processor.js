
class PCMProcessor extends AudioWorkletProcessor {
    process(inputs) {
        const input = inputs[0];
        const channel = input && input[0];

        if (channel) {
            this.port.postMessage(channel.slice());
        }

        return true;
    }
}

registerProcessor("pcm-processor", PCMProcessor);
