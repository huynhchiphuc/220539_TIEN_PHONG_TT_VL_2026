import FileUpload from '../components/FileUpload';
import './Upload.css';

const Upload = () => {
  return (
    <div className="upload-page">
      <h1>Upload Your Files</h1>
      <FileUpload />
    </div>
  );
};

export default Upload;
