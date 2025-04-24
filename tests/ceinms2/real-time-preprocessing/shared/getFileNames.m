function [ subFileList ] = getFileNames( baseDir )
%GETDIRNAMES Summary of this function goes here
%   Detailed explanation goes here

d = dir(char(baseDir));
isub = [d(:).isdir]; % returns logical vector
subFileList = {d(isub).name}';
subFileList(ismember(subFileList,{'.','..'})) = [];

end