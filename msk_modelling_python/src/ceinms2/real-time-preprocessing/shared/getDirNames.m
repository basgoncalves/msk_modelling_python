function [ subDirList ] = getDirNames( baseDir )
%GETDIRNAMES Summary of this function goes here
%   Detailed explanation goes here

d = dir(char(baseDir));
isub = [d(:).isdir]; % returns logical vector
subDirList = {d(isub).name}';
subDirList(ismember(subDirList,{'.','..'})) = [];

end

