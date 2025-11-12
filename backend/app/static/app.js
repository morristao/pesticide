const form = document.querySelector('#inference-form');
const modelSelect = document.querySelector('#model-select');
const statusBox = document.querySelector('#status');
const resultBox = document.querySelector('#result-json');

async function loadModels() {
  try {
    const res = await fetch('/api/v1/models');
    if (!res.ok) {
      throw new Error('Failed to fetch models');
    }
    const models = await res.json();
    modelSelect.innerHTML = '';
    models.forEach((model) => {
      const option = document.createElement('option');
      option.value = model.id;
      option.textContent = `${model.name} (v${model.version})`;
      modelSelect.appendChild(option);
    });
  } catch (err) {
    statusBox.textContent = err.message;
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!modelSelect.value) {
    statusBox.textContent = 'Model is required';
    return;
  }

  const formData = new FormData();
  const file = document.querySelector('#image-input').files[0];
  if (!file) {
    statusBox.textContent = 'Please attach an image.';
    return;
  }

  formData.append('model_id', modelSelect.value);
  formData.append('image', file);

  form.querySelector('button').disabled = true;
  statusBox.textContent = 'Running model...';

  try {
    const res = await fetch('/api/v1/infer', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const message = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(message.detail || 'Inference failed');
    }

    const payload = await res.json();
    statusBox.textContent = 'Prediction ready';
    resultBox.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    statusBox.textContent = error.message;
  } finally {
    form.querySelector('button').disabled = false;
  }
});

loadModels();
