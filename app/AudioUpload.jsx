'use client'
import { useState, useEffect } from 'react';
import { CircularProgress } from '@mui/material';

const AudioUpload = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [results, setResults] = useState('');
  const [loading, setLoading] = useState(false);
  const [startTime, setStartTime] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(null);

  useEffect(() => {
    let interval;
    if (loading) {
      setStartTime(Date.now());
      interval = setInterval(() => {
        setElapsedTime(((Date.now() - startTime) / 1000).toFixed(2)); // Update every second
      }, 1000);
    } else if (startTime) {
      clearInterval(interval);
      setElapsedTime(((Date.now() - startTime) / 1000).toFixed(2));
      setStartTime(null); // Reset start time
    }

    return () => clearInterval(interval); // Clean up interval on unmount
  }, [loading, startTime]);

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
      setLoading(true);
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
    setLoading(false);
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
      {loading ? (
        <>
          <CircularProgress />
          <p>Loading... {elapsedTime} seconds</p>
        </>
      ) : (
        <div>
          {results.key}
          {results.tempo}
          {elapsedTime && <p>Time taken: {elapsedTime} seconds</p>}
        </div>
      )}
    </div>
  );
};

export default AudioUpload;
