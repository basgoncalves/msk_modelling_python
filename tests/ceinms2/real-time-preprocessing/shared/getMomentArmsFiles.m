function [ momentArmsData ] = getMomentArmsFiles( baseDir, name ,trialFilename)
%GETEMGFILE Summary of this function goes here
%   Detailed explanation goes here
possibleFiles = dir([baseDir '\*' name '*']);
momentArmsData = {};
files = {possibleFiles.name};
for i = 1:length(files)
    currentFile = files{i};
    ind=strfind(currentFile, name);
    momentArmsData{i}.file = [baseDir '\' files{i}];
    momentArmsData{i}.dof = currentFile(ind+length(name):end-4);
    if nargin == 3
        momentArmsData{i}.file = relativepath(momentArmsData{i}.file,trialFilename);
    end
end
end
