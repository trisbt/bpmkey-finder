'use client'
import { useState } from 'react';

const AudioUpload = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [results, setResults] = useState('');

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    setSelectedFile(file);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const handleUpload = async () => {
    try {
      if (!selectedFile) {
        alert('Please select a file to upload.');
        return;
      }

      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch('/api/python', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        console.log(result);
        setResults(result);
      } else {
        console.error('Failed to upload file.');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };
  const handleRemove = () => {
    setSelectedFile(null);
    setResults(''); // Clear results when removing the file
  };
  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        style={{ border: '1px dashed #ccc', padding: '20px', textAlign: 'center' }}
      >
{selectedFile ? (
          <div>
            <p>Selected File: {selectedFile.name}</p>
            <button onClick={handleRemove}>Remove</button>
          </div>
        ) : (
          <p>Drag and drop a file here or click to select</p>
        )}      </div>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload}>Analyze</button>
      {results && (
        <div>
          {results.key}
          {results.tempo}
        </div>
      )}
    </div>
  );
};

export default AudioUpload;
