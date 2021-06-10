from dataclasses import dataclass

@dataclass(frozen=True)
class SQL:
    check_task = """
        SELECT count(task_id)
        FROM TaskStates
        WHERE task_id = {id}
    """

    get_task_info = """
        SELECT DISTINCT TI.try_iter, task_repo, task_owner
        FROM Tasks_buffer
        LEFT JOIN
            (SELECT task_id, concat(toString(task_try), '.', toString(task_iter)) AS try_iter
            FROM TaskIterations_buffer) AS TI USING task_id
        WHERE task_id = {id}
    """

    get_task_content = """
        SELECT titer_srcrpm_hash,
            TS.task_state AS status,
            subtask_id,
            concat(toString(task_try), '.', toString(task_iter)) AS ti,
            groupUniqArray(arrayJoin(titer_pkgs_hash)),
            any(TS.task_message) as message
        FROM TaskIterations_buffer
        CROSS JOIN (SELECT argMax(task_state, task_changed) AS task_state,
                        argMax(task_message, task_changed) AS task_message
                    FROM TaskStates_buffer
                    WHERE task_id = {id}) AS TS
        WHERE task_id = {id}
            AND (task_try, task_iter) IN
                (SELECT argMax(task_try, task_changed),
                    argMax(task_iter, task_changed)
                FROM TaskIterations_buffer
                WHERE task_id = {id})
        GROUP BY titer_srcrpm_hash,
                status,
                subtask_id,
                ti
        ORDER BY subtask_id
    """

    get_task_content_rebuild = """
        SELECT titer_srcrpm_hash,
            TS.task_state AS status,
            subtask_id,
            concat(toString(task_try), '.', toString(task_iter)) AS ti,
            groupUniqArray(arrayJoin(titer_pkgs_hash)),
            any(TS.task_message) as message
        FROM TaskIterations_buffer
        CROSS JOIN (SELECT argMax(task_state, task_changed) AS task_state,
                        argMax(task_message, task_changed) AS task_message
                    FROM TaskStates_buffer
                    WHERE task_id = {id}) AS TS
        WHERE task_id = {id}
            AND (task_try, task_iter) = {ti}
        GROUP BY titer_srcrpm_hash,
                status,
                subtask_id,
                ti
        ORDER BY subtask_id
    """

    get_packages_info = """
        SELECT pkg_hash,
            pkg_name,
            pkg_version,
            pkg_release,
            pkg_arch,
            pkg_description
        FROM Packages_buffer
        WHERE pkg_hash IN {hshs}
    """

    get_task_approvals = """
        SELECT res
        FROM(
            SELECT argMax(tuple(subtask_id, toString(tapp_date), tapp_type,
                tapp_name, tapp_message, tapp_revoked), ts) AS res
            FROM TaskApprovals
            WHERE task_id = {id}
            GROUP BY (subtask_id, tapp_name)
        ) WHERE tupleElement(res, 6) = 0
    """

