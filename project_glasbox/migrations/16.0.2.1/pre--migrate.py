def migrate(cr, version):
    # customization has parent, child
    # oob has child, parent.
    # old query
    query = """
    delete from project_depending_tasks where task_id=depending_task_id;
    delete from project_depending_tasks where id not in (select max(id) from project_depending_tasks group by task_id, depending_task_id);
    INSERT INTO task_dependencies_rel(task_id, depends_on_id)
    SELECT depending_task_id, task_id FROM project_depending_tasks;
    UPDATE project_task 
    SET planned_date_begin = date_start, planned_date_end = date_end
    WHERE date_end > date_start;
    """
    cr.execute(query)
