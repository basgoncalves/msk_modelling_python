function [ file ] = getFile( baseDir, name )
%GETEMGFILE Summary of this function goes here
%   Detailed explanation goes here
   possibleFiles = dir([baseDir '\*' name '.*']);
   file = [];
   if(length(possibleFiles) ~= 1)
       file = uigetfile(baseDir, ['select ' name ' file']);
   else
       file = possibleFiles.name;
   end
   file = [baseDir '\' file];

end

