import tensorflow as tf


def convert_tacotron2_to_tflite(model,
                                output_path=None,
                                experimental_converter=True):
    """Convert Tensorflow Tacotron2 model to TFLite. Save a binary file if output_path is
    provided, else return TFLite model."""

    concrete_function = model.inference_tflite.get_concrete_function()
    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [concrete_function])
    converter.experimental_new_converter = experimental_converter
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS, tf.lite.OpsSet.SELECT_TF_OPS
    ]
    tflite_model = converter.convert()
    if output_path is not None:
        # same model binary if outputpath is provided
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        return None
    return tflite_model


def load_tflite_model(tflite_path):
    tflite_model = tf.lite.Interpreter(model_path=tflite_path)
    tflite_model.allocate_tensors()
    return tflite_model