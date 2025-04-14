function [val] = toMatlab(in)

%TOMATLAB Summary of this function goes here
%   Detailed explanation goes here
    val = NaN;
   % try
        className = char(in.getClass().getName());
        switch className
            case 'org.opensim.modeling.ArrayDouble'
                val = fromArrayDouble(in);
            case 'org.opensim.modeling.Storage'
                val = fromStorage(in);
            case 'org.opensim.modeling.ArrayStr'
                val = fromArrayStr(in);
            case 'org.opensim.modeling.Vec3'
                val = fromVec3(in);
        end
 %   catch err
%        val = NaN;
 %   end

end

function r = fromStorage(in)
import org.opensim.modeling.*
    try
        r.labels = fromArrayStr(in.getColumnLabels());
        r.values = zeros(in.getSize(), length(r.labels));
        timeArrDbl = ArrayDouble();
        in.getTimeColumn(timeArrDbl);
        r.values(:,1) = fromArrayDouble(timeArrDbl);
        for i = 0:(length(r.labels)-2)
            colArrDbl = ArrayDouble();
            in.getDataColumn(i, colArrDbl);
            r.values(:,i+2) = fromArrayDouble(colArrDbl);
        end
    catch err
        rethrow(err);
    end
end

function r = fromArrayDouble(in)
    r = NaN;
    try
        for i = 0:(in.getSize()-1)
            r(i+1) = in.getitem(i);
        end
        r = r';
    catch err
        rethrow(err);
    end
end


function r = fromArrayStr(in)
    try
        for i = 0:(in.getSize()-1)
            r{i+1} = char(in.getitem(i));
        end
    catch err
        rethrow(err);
    end

end

function r = fromVec3(in)
    r = [0,0,0];
    try
        for i = 1:3
            r(i) = in.get(i-1);
        end
    catch err
        rethrow(err);
    end

end
