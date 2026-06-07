const fs = require('fs');

const fullJSX = fs.readFileSync('frontend/src/pages/ComicGenerator.jsx', 'utf8');

const startToken = '<div className="settings-content">';
const startIdx = fullJSX.indexOf(startToken);
const btnIdx = fullJSX.indexOf('<button', startIdx);
const beforeBtn = fullJSX.substring(startIdx, btnIdx);
const lastDivIdx = beforeBtn.lastIndexOf('</div>');
const blockToReplace = beforeBtn.substring(0, lastDivIdx + 6); // Includes the last </div>

// Just save it to check
fs.writeFileSync('blockToReplace.jsx', blockToReplace);
